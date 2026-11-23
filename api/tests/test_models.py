from sqlalchemy import Table

from app.config import Settings
from app.db import Base
from app.models import ChatTrace, Chunk, Document, IngestJob


def test_metadata_registers_all_tables() -> None:
    models = (Document, Chunk, IngestJob, ChatTrace)
    assert {model.__tablename__ for model in models} <= set(Base.metadata.tables)


def test_chunks_tsvector_is_generated_from_spanish_text() -> None:
    chunks: Table = Base.metadata.tables["chunks"]
    computed = chunks.c.tsv.computed
    assert computed is not None
    assert str(computed.sqltext) == "to_tsvector('spanish', text)"


def test_chunks_indexes_cover_embedding_and_tsv() -> None:
    chunks: Table = Base.metadata.tables["chunks"]
    indexes = {index.name: index for index in chunks.indexes}
    hnsw = indexes["ix_chunks_embedding_hnsw"].dialect_options["postgresql"]
    assert hnsw["using"] == "hnsw"
    assert hnsw["ops"]["embedding"] == "vector_cosine_ops"
    assert indexes["ix_chunks_tsv_gin"].dialect_options["postgresql"]["using"] == "gin"


def test_chunk_embedding_has_768_dimensions() -> None:
    chunks: Table = Base.metadata.tables["chunks"]
    assert chunks.c.embedding.type.dim == 768


def test_settings_keep_secret_out_of_repr() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@host/db",
        gemini_api_key="top-secret",
        chemlab_api_key="test"
    )
    assert settings.embedding_dim == 768
    assert settings.environment == "local"
    assert "top-secret" not in repr(settings)
