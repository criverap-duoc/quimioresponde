"""Ingesta desde bytes, sin descarga, del fixture real de BCN (Testcontainers)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.ingest import pipeline
from app.llm.embeddings import EmbeddingClient
from app.models.chunk import EMBEDDING_DIM, Chunk
from app.retrieval.bcn import cargar_fixture

pytestmark = pytest.mark.integration


async def test_ingest_from_bytes_es_idempotente(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw, url = cargar_fixture("decreto_43")

    async def embed_trivial(self: EmbeddingClient, texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    monkeypatch.setattr(EmbeddingClient, "embed", embed_trivial)
    monkeypatch.setattr(
        pipeline,
        "get_settings",
        lambda: Settings(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            gemini_api_key="test-key",
        ),
    )

    first = await pipeline.ingest_from_bytes("decreto_43", raw, url, session)
    second = await pipeline.ingest_from_bytes("decreto_43", raw, url, session)

    assert isinstance(first, pipeline.Ingested)
    assert first.chunks_count == 244
    assert isinstance(second, pipeline.AlreadyIngested)
    assert second.document_id == first.document_id
    assert await session.scalar(select(func.count()).select_from(Chunk)) == first.chunks_count
