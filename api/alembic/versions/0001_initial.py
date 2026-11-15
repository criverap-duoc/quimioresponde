"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-14
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE documents (
            id UUID PRIMARY KEY,
            source TEXT NOT NULL,
            norma TEXT NOT NULL,
            version_hash TEXT NOT NULL UNIQUE,
            vigente BOOLEAN NOT NULL DEFAULT true,
            url TEXT NOT NULL,
            raw_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE chunks (
            id UUID PRIMARY KEY,
            document_id UUID NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
            article TEXT NOT NULL,
            numeral TEXT,
            text TEXT NOT NULL,
            embedding vector(768) NOT NULL,
            tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('spanish', text)) STORED,
            url TEXT NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_chunks_document_id ON chunks (document_id)")
    op.execute(
        """
        CREATE INDEX ix_chunks_embedding_hnsw ON chunks
        USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
        """
    )
    op.execute("CREATE INDEX ix_chunks_tsv_gin ON chunks USING gin (tsv)")

    op.execute("CREATE TYPE ingest_job_status AS ENUM ('pending', 'running', 'done', 'failed')")
    op.execute(
        """
        CREATE TABLE ingest_jobs (
            id UUID PRIMARY KEY,
            idempotency_key TEXT NOT NULL UNIQUE,
            status ingest_job_status NOT NULL DEFAULT 'pending',
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE chat_traces (
            id UUID PRIMARY KEY,
            request_id TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            citation_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_chat_traces_request_id ON chat_traces (request_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_traces")
    op.execute("DROP TABLE IF EXISTS ingest_jobs")
    op.execute("DROP TYPE IF EXISTS ingest_job_status")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS documents")
