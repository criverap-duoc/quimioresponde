"""Arranque del worker de ingesta desde el lifespan de FastAPI."""

import asyncio

from app.ingest import queue


async def start_worker() -> asyncio.Task[None]:
    """Arranca el consumidor de la cola de ingesta como tarea de fondo."""
    return asyncio.create_task(queue.run_forever(), name="ingest-worker")
