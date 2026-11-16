"""Fixtures compartidas por los tests de integración con Postgres y pgvector."""

from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.db import Base


@pytest.fixture(scope="module")
def postgres_url() -> Iterator[str]:
    """Contenedor Postgres con pgvector reutilizado por módulo de tests."""
    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as container:
        yield container.get_connection_url()


@pytest.fixture
async def session(postgres_url: str) -> AsyncIterator[AsyncSession]:
    """Sesión async con el esquema del proyecto creado en el contenedor."""
    engine = create_async_engine(postgres_url)
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()
