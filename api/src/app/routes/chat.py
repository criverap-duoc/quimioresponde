"""Endpoint `/chat`: recupera, verifica citas y streamea la respuesta por SSE."""

import json
import logging
import uuid
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
from starlette.responses import Response

from app.config import get_settings
from app.db import get_session, get_sessionmaker
from app.errors import problem_body
from app.llm.client import GeminiClient, LLMClient
from app.llm.prompt import build_prompt
from app.llm.schemas import Answer
from app.llm.verifier import CitationRejected, verify
from app.models.chat_trace import ChatTrace
from app.retrieval.search import search

_CHUNK_SIZE = 20
_TOP_K = 5
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()


class ChatRequest(BaseModel):
    """Pregunta del usuario."""

    question: str = Field(min_length=1, max_length=1000)


@router.post("/chat")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    payload: ChatRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Responde con citas verificadas, en streaming SSE."""
    hits = await search(session, payload.question, k=_TOP_K)
    answer = cast(Answer, await _client().complete(build_prompt(payload.question, hits), Answer))
    try:
        verify(answer, hits)
    except CitationRejected as exc:
        return EventSourceResponse(_stream_error(request, exc))
    return EventSourceResponse(_stream_answer(answer, uuid.uuid4().hex, payload.question))


def _client() -> LLMClient:
    """Cliente Gemini configurado por entorno."""
    settings = get_settings()
    return GeminiClient(
        api_key=settings.gemini_api_key.get_secret_value(), model=settings.gemini_model
    )


async def _stream_answer(
    answer: Answer, request_id: str, question: str
) -> AsyncIterator[dict[str, str]]:
    """Emite citas, la respuesta troceada y el cierre; luego persiste la traza."""
    citations = [citation.model_dump() for citation in answer.citations]
    yield {"event": "citations", "data": json.dumps(citations, ensure_ascii=False)}
    # Troceado artificial para la UX: el LLM ya terminó. Streaming real del SDK, en Fase 3.
    text = answer.answer if answer.answer else (answer.refusal_reason or "")
    for start in range(0, len(text), _CHUNK_SIZE):
        yield {"event": "answer", "data": text[start : start + _CHUNK_SIZE]}
    # El SDK aún no expone uso de tokens estable; se rellena en Fase 3.
    yield {"event": "done", "data": "{}"}
    await _record_trace(request_id, question, answer)


async def _stream_error(request: Request, exc: CitationRejected) -> AsyncIterator[dict[str, str]]:
    """Emite el rechazo como `problem+json` dentro del propio stream."""
    body = problem_body(
        request, 502, "citation_rejected", "Respuesta sin citas verificables", exc.reason.value
    )
    yield {"event": "error", "data": json.dumps(body, ensure_ascii=False)}


async def _record_trace(request_id: str, question: str, answer: Answer) -> None:
    """Guarda la traza con sesión propia: la de la request ya se cerró."""
    trace = ChatTrace(
        request_id=request_id,
        question=question,
        answer=answer.answer,
        citation_ids=[citation.chunk_id for citation in answer.citations],
        cost_usd=Decimal(0),
    )
    try:
        async with get_sessionmaker()() as session:
            session.add(trace)
            await session.commit()
    except (SQLAlchemyError, OSError) as exc:  # borde: la respuesta ya se envió
        logger.warning("traza %s no guardada: %s", request_id, exc)
