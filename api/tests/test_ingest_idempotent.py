"""Ingesta idempotente contra Postgres con pgvector (Testcontainers)."""

from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.ingest import pipeline
from app.llm.embeddings import EmbeddingClient
from app.models.chunk import EMBEDDING_DIM, Chunk
from app.models.document import Document
from app.models.ingest_job import IngestJob, IngestJobStatus
from app.retrieval.bcn import DECRETO_43_URL
from app.retrieval.hashing import idempotency_key, version_hash

pytestmark = pytest.mark.integration

_FIXTURE = Path(__file__).parent / "fixtures" / "bcn_decreto43_articulo.html"


async def test_ingest_is_idempotent_by_version_hash(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _FIXTURE.read_bytes()

    async def fetch_local(url: str) -> bytes:
        return raw

    async def embed_trivial(self: EmbeddingClient, texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_DIM for _ in texts]

    monkeypatch.setattr(pipeline, "fetch_norma", fetch_local)
    monkeypatch.setattr(EmbeddingClient, "embed", embed_trivial)
    monkeypatch.setattr(
        pipeline,
        "get_settings",
        lambda: Settings(
            database_url="postgresql+asyncpg://test:test@localhost/test",
            gemini_api_key="test-key",
        ),
    )

    first = await pipeline.ingest("decreto_43", DECRETO_43_URL, session)
    second = await pipeline.ingest("decreto_43", DECRETO_43_URL, session)

    assert isinstance(first, pipeline.Ingested)
    assert first.chunks_count >= 1
    assert isinstance(second, pipeline.AlreadyIngested)
    assert second.document_id == first.document_id
    assert await session.scalar(select(func.count()).select_from(Document)) == 1
    assert await session.scalar(select(func.count()).select_from(Chunk)) == first.chunks_count

    job = await session.scalar(select(IngestJob))
    assert job is not None
    assert job.status is IngestJobStatus.DONE
    assert job.idempotency_key == idempotency_key("decreto_43", version_hash(raw))
