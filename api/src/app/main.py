"""Aplicación FastAPI con healthchecks de liveness y readiness."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import get_engine
from app.errors import install_error_handlers, problem

_DB_TIMEOUT = 2.0
_WARM_TIMEOUT = 10.0
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Calienta el pool: el handshake de Neon (3-6 s) excede el timeout de 2 s de /readyz."""
    try:
        async with asyncio.timeout(_WARM_TIMEOUT), get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # best-effort: la app arranca aunque Neon esté caído
        logger.warning("warm del pool falló: %s", exc)
    yield


app = FastAPI(title="QuimioResponde API", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness: no verifica dependencias externas."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Readiness: base de datos alcanzable y API key del LLM presente."""
    try:
        settings = get_settings()
    except ValidationError:
        return problem(
            request, 503, "configuration_missing", "Configuración incompleta", "Faltan variables."
        )
    if not await _db_reachable():
        return problem(
            request,
            503,
            "database_unavailable",
            "Base de datos no disponible",
            "SELECT 1 no respondió en 2 s.",
        )
    if not settings.gemini_api_key.get_secret_value():
        return problem(
            request, 503, "llm_not_configured", "LLM no configurado", "Falta GEMINI_API_KEY."
        )
    return JSONResponse({"status": "ok"})


async def _db_reachable() -> bool:
    """Comprueba la conexión con `SELECT 1` bajo un timeout acotado."""
    try:
        async with asyncio.timeout(_DB_TIMEOUT), get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    except (TimeoutError, SQLAlchemyError, OSError):
        return False
    return True


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
