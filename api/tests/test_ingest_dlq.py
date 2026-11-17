"""DLQ en memoria y cota de la cola de ingesta."""

import asyncio
from typing import cast

import pytest

from app.ingest import pipeline
from app.ingest.queue import MAX_ATTEMPTS, IngestQueue, QueueFullError, SessionFactory
from app.retrieval.bcn import DECRETO_43_URL


class _StubSession:
    async def __aenter__(self) -> "_StubSession":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


def _stub_session() -> _StubSession:
    return _StubSession()


def _queue(maxsize: int) -> IngestQueue:
    return IngestQueue(cast(SessionFactory, _stub_session), maxsize=maxsize)


async def _esperar_dlq(queue: IngestQueue) -> None:
    for _ in range(100):
        if queue.dead_letters:
            return
        await asyncio.sleep(0.02)
    raise AssertionError("el job fallido no llegó a la DLQ")


async def test_failed_job_lands_in_dlq_and_worker_survives(monkeypatch: pytest.MonkeyPatch) -> None:
    async def falla(norma: str, url: str, session: object) -> None:
        raise RuntimeError("gemini caído")

    monkeypatch.setattr(pipeline, "ingest", falla)
    queue = _queue(maxsize=3)
    worker = asyncio.create_task(queue.run_forever())
    try:
        await queue.submit("decreto_43", DECRETO_43_URL)
        await asyncio.wait_for(_esperar_dlq(queue), timeout=2)

        assert len(queue.dead_letters) == 1
        assert queue.dead_letters[0].job.norma == "decreto_43"
        assert "RuntimeError" in queue.dead_letters[0].error
        assert not worker.done()
    finally:
        worker.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker


async def test_job_hits_dlq_after_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    async def falla(norma: str, url: str, session: object) -> None:
        attempts.append(norma)
        raise RuntimeError("gemini caído")

    monkeypatch.setattr(pipeline, "ingest", falla)
    queue = _queue(maxsize=3)
    worker = asyncio.create_task(queue.run_forever())
    try:
        await queue.submit("decreto_43", DECRETO_43_URL)
        await asyncio.wait_for(_esperar_dlq(queue), timeout=2)

        assert len(attempts) == MAX_ATTEMPTS
        assert len(queue.dead_letters) == 1
    finally:
        worker.cancel()
        with pytest.raises(asyncio.CancelledError):
            await worker


async def test_submit_raises_queue_full_when_saturated() -> None:
    queue = _queue(maxsize=1)

    await queue.submit("decreto_43", DECRETO_43_URL)
    with pytest.raises(QueueFullError):
        await queue.submit("decreto_43", DECRETO_43_URL)
