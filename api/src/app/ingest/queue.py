"""Cola acotada de ingesta con concurrencia limitada y DLQ en memoria."""

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_sessionmaker
from app.ingest import pipeline

logger = logging.getLogger(__name__)

QUEUE_MAXSIZE = 3
MAX_CONCURRENT_INGESTS = 2
MAX_ATTEMPTS = 3

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


class QueueFullError(Exception):
    """La cola está llena; el endpoint de ingesta la traduce a 429 + Retry-After."""


@dataclass(frozen=True)
class Job:
    """Solicitud de ingesta encolada, con identificador para trazar logs."""

    norma: str
    url: str
    request_id: str


@dataclass(frozen=True)
class DeadLetter:
    """Job que agotó sus intentos y quedó fuera de la cola."""

    job: Job
    error: str


class IngestQueue:
    """Cola FIFO acotada que ejecuta la ingesta con concurrencia limitada."""

    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        *,
        maxsize: int = QUEUE_MAXSIZE,
        concurrency: int = MAX_CONCURRENT_INGESTS,
    ) -> None:
        self._session_factory = session_factory
        self._queue: asyncio.Queue[Job] = asyncio.Queue(maxsize=maxsize)
        self._semaphore = asyncio.Semaphore(concurrency)
        self._dead_letters: list[DeadLetter] = []
        self._tasks: set[asyncio.Task[None]] = set()

    @property
    def dead_letters(self) -> tuple[DeadLetter, ...]:
        """Jobs que agotaron sus intentos."""
        return tuple(self._dead_letters)

    async def submit(self, norma: str, url: str) -> None:
        """Encola una ingesta o falla con `QueueFullError` si no hay cupo."""
        job = Job(norma=norma, url=url, request_id=uuid.uuid4().hex)
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            _log(logging.WARNING, "ingest_queue_full", job)
            raise QueueFullError(f"cola de ingesta llena: {self._queue.maxsize} jobs") from None
        _log(logging.INFO, "ingest_enqueued", job, position=self._queue.qsize())

    async def run_forever(self) -> None:
        """Consume la cola sin término; cada job fallido termina en la DLQ."""
        while True:
            job = await self._queue.get()
            task = asyncio.create_task(self._process(job))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _process(self, job: Job) -> None:
        async with self._semaphore:
            error = ""
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    async with self._session() as session:
                        await pipeline.ingest(job.norma, job.url, session)
                except Exception as exc:  # borde del worker: nada escapa a la tarea
                    error = f"{type(exc).__name__}: {exc}"
                    _log(
                        logging.WARNING, "ingest_attempt_failed", job, attempt=attempt, error=error
                    )
                    continue
                _log(logging.INFO, "ingest_done", job, attempt=attempt)
                return
            self._dead_letters.append(DeadLetter(job=job, error=error))
            _log(logging.ERROR, "ingest_dead_letter", job, error=error)

    def _session(self) -> AbstractAsyncContextManager[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = get_sessionmaker()
        return self._session_factory()


def _log(level: int, event: str, job: Job, **fields: object) -> None:
    payload = {
        "event": event,
        "request_id": job.request_id,
        "norma": job.norma,
        "url": job.url,
        **fields,
    }
    logger.log(level, json.dumps(payload, ensure_ascii=False))


_default_queue: IngestQueue | None = None


def get_queue() -> IngestQueue:
    """Devuelve la cola de ingesta compartida del proceso."""
    global _default_queue
    if _default_queue is None:
        _default_queue = IngestQueue()
    return _default_queue


async def submit(norma: str, url: str) -> None:
    """Encola una ingesta en la cola compartida."""
    await get_queue().submit(norma, url)


async def run_forever() -> None:
    """Consume la cola compartida hasta que se cancele la tarea."""
    await get_queue().run_forever()
