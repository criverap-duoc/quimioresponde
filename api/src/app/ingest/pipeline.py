"""Orquestación idempotente de la ingesta de normas desde BCN."""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm.embeddings import EmbeddingClient
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.ingest_job import IngestJob, IngestJobStatus
from app.retrieval.bcn import fetch_norma, parse_html
from app.retrieval.hashing import idempotency_key, version_hash

logger = logging.getLogger(__name__)

SOURCE_BCN = "BCN"


@dataclass(frozen=True)
class Ingested:
    """La norma se descargó y persistió con sus chunks."""

    document_id: uuid.UUID
    chunks_count: int


@dataclass(frozen=True)
class AlreadyIngested:
    """El hash de versión ya estaba en `documents`: no se escribió nada."""

    document_id: uuid.UUID


IngestResult = Ingested | AlreadyIngested


def embedding_client() -> EmbeddingClient:
    """Construye el cliente de embeddings con la configuración vigente."""
    settings = get_settings()
    return EmbeddingClient(
        api_key=settings.gemini_api_key.get_secret_value(), model=settings.embedding_model
    )


async def ingest(norma: str, url: str, session: AsyncSession) -> IngestResult:
    """Descarga, trocea y persiste una norma; idempotente por hash de versión."""
    raw = await fetch_norma(url)
    return await ingest_from_bytes(norma, raw, url, session)


async def ingest_from_bytes(
    norma: str, raw: bytes, url_origen: str, session: AsyncSession
) -> IngestResult:
    """Trocea y persiste una norma ya descargada; idempotente por hash de versión."""
    vhash = version_hash(raw)
    existing_id = await session.scalar(select(Document.id).where(Document.version_hash == vhash))
    if existing_id is not None:
        logger.info("norma ya ingestada: norma=%s version_hash=%s", norma, vhash[:12])
        return AlreadyIngested(document_id=existing_id)

    drafts = parse_html(raw, norma, url_origen)
    vectors = await embedding_client().embed([draft.text for draft in drafts])

    document = Document(
        source=SOURCE_BCN,
        norma=norma,
        version_hash=vhash,
        vigente=True,
        url=url_origen,
        raw_text=raw.decode("utf-8", errors="replace"),
    )
    session.add(document)
    await session.flush()
    document_id = document.id
    session.add_all(
        [
            Chunk(
                document_id=document_id,
                article=draft.article,
                numeral=draft.numeral,
                text=draft.text,
                embedding=vector,
                url=draft.url,
            )
            for draft, vector in zip(drafts, vectors, strict=True)
        ]
    )
    session.add(
        IngestJob(idempotency_key=idempotency_key(norma, vhash), status=IngestJobStatus.DONE)
    )
    await session.commit()

    logger.info("norma ingestada: norma=%s chunks=%d", norma, len(drafts))
    return Ingested(document_id=document_id, chunks_count=len(drafts))
