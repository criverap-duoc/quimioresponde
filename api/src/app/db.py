from collections.abc import AsyncIterator
from typing import Any

from pgvector import Vector
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _encode_vector(value: list[float] | str) -> str:
    """Acepta el texto que ya serializó SQLAlchemy y listas de asyncpg puro."""
    return value if isinstance(value, str) else Vector(value).to_text()


async def _register_vector(conn: Any) -> None:
    """Registra el codec de `vector` en formato texto.

    `pgvector.asyncpg.register_vector` usa formato binario y rechaza el texto que
    serializa el tipo `VECTOR` de SQLAlchemy, así que se registra en texto y se
    acepta tanto el texto ya serializado como listas de asyncpg puro.
    """
    await conn.set_type_codec(
        "vector",
        schema="public",
        format="text",
        encoder=_encode_vector,
        decoder=Vector.from_text,
    )


def _on_connect(dbapi_connection: Any, _: Any) -> None:
    dbapi_connection.run_async(_register_vector)


_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Devuelve el engine async compartido, creándolo en el primer uso."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
        event.listen(_engine.sync_engine, "connect", _on_connect)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dependencia de FastAPI: una sesión por request."""
    async with get_sessionmaker()() as session:
        yield session
