"""Errores HTTP en formato `application/problem+json` (RFC 9457)."""

from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.types import ExceptionHandler

from app.llm.client import LLMRateLimited, LLMResponseError, LLMUnavailable
from app.retrieval.bcn import NormaFetchError, NormaParseError

CONTENT_TYPE = "application/problem+json"


def problem(
    request: Request,
    status: int,
    kind: str,
    title: str,
    detail: Any,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Construye una respuesta de problema con la ruta como `instance`."""
    body = {
        "type": kind,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
    }
    return JSONResponse(body, status_code=status, media_type=CONTENT_TYPE, headers=headers)


async def _validation(request: Request, exc: Exception) -> JSONResponse:
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    return problem(request, 422, "validation", "Entrada inválida", jsonable_encoder(errors))


async def _rate_limited(request: Request, exc: Exception) -> JSONResponse:
    retry_after = exc.retry_after if isinstance(exc, LLMRateLimited) else None
    headers = {"Retry-After": f"{retry_after:g}"} if retry_after is not None else None
    return problem(
        request, 429, "rate_limited", "Límite de uso alcanzado", "Reintenta más tarde.", headers
    )


def _fixed(status: int, kind: str, title: str, detail: str | None = None) -> ExceptionHandler:
    async def handle(request: Request, exc: Exception) -> JSONResponse:
        return problem(request, status, kind, title, detail or str(exc))

    return handle


def install_error_handlers(app: FastAPI) -> None:
    """Registra los handlers tipados de la API."""
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(LLMRateLimited, _rate_limited)
    app.add_exception_handler(
        LLMUnavailable,
        _fixed(503, "llm_unavailable", "LLM no disponible", "El modelo no respondió; reintenta."),
    )
    app.add_exception_handler(
        LLMResponseError,
        _fixed(502, "llm_invalid_response", "Respuesta inválida", "El JSON no validó el esquema."),
    )
    app.add_exception_handler(NormaFetchError, _fixed(502, "norma_fetch", "Norma no descargable"))
    app.add_exception_handler(NormaParseError, _fixed(500, "norma_parse", "Norma no procesable"))
