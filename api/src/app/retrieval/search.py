"""Recuperación híbrida de chunks normativos con fusión RRF."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm.embeddings import EmbeddingClient
from app.models.chunk import Chunk

_CANDIDATOS = 30


@dataclass(frozen=True)
class Hit:
    """Trozo normativo recuperado con su puntuación de fusión."""

    chunk_id: str
    document_id: str
    article: str
    numeral: str | None
    text: str
    url: str
    score: float


def rrf_fuse(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fusiona listas de chunk_id ordenadas por relevancia con Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            if chunk_id not in first_seen:
                first_seen[chunk_id] = len(first_seen)
                scores[chunk_id] = 0.0
            scores[chunk_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], first_seen[item[0]]))


async def search(session: AsyncSession, query: str, k: int = 10) -> list[Hit]:
    """Recupera chunks por similitud vectorial y full-text español, fusionados con RRF."""
    settings = get_settings()
    client = EmbeddingClient(
        api_key=settings.gemini_api_key.get_secret_value(), model=settings.embedding_model
    )
    vector = (await client.embed([query]))[0]
    vector_ids = await _vector_ids(session, vector)
    text_ids = await _text_ids(session, query)
    fused = rrf_fuse([vector_ids, text_ids])[:k]
    if not fused:
        return []
    statement = select(Chunk).where(Chunk.id.in_([uuid.UUID(chunk_id) for chunk_id, _ in fused]))
    chunks = {str(chunk.id): chunk for chunk in await session.scalars(statement)}
    return [_to_hit(chunks[chunk_id], score) for chunk_id, score in fused if chunk_id in chunks]


async def _vector_ids(session: AsyncSession, vector: list[float]) -> list[str]:
    statement = (
        select(Chunk.id).order_by(Chunk.embedding.cosine_distance(vector)).limit(_CANDIDATOS)
    )
    return [str(chunk_id) for chunk_id in await session.scalars(statement)]


async def _text_ids(session: AsyncSession, query: str) -> list[str]:
    tsquery = func.websearch_to_tsquery("spanish", query)
    statement = (
        select(Chunk.id)
        .where(Chunk.tsv.op("@@")(tsquery))
        .order_by(func.ts_rank(Chunk.tsv, tsquery).desc())
        .limit(_CANDIDATOS)
    )
    return [str(chunk_id) for chunk_id in await session.scalars(statement)]


def _to_hit(chunk: Chunk, score: float) -> Hit:
    return Hit(
        chunk_id=str(chunk.id),
        document_id=str(chunk.document_id),
        article=chunk.article,
        numeral=chunk.numeral,
        text=chunk.text,
        url=chunk.url,
        score=score,
    )
