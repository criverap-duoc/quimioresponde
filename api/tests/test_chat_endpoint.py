"""Endpoint /chat: streaming SSE, rechazo de citas, rate limit y CORS."""

from collections.abc import AsyncIterator, Iterator
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.db import get_session
from app.llm.schemas import Answer, Citation
from app.main import app
from app.models.chat_trace import ChatTrace
from app.retrieval.search import Hit
from app.routes import chat

_QUESTION = {"question": "¿Qué dice el artículo 1 del Decreto 43?"}


def _hit(chunk_id: str, article: str, text: str) -> Hit:
    return Hit(chunk_id, "d1", article, None, text, "https://example.test/d43", 0.9)


_HITS = [
    _hit("c1", "Artículo 1", "Almacenar ácidos y bases por separado."),
    _hit("c2", "Artículo 2", "Usar guantes y gafas al manipular corrosivos."),
]
_ANSWER = Answer(
    answer="Separa ácidos y bases y usa protección.",
    citations=[
        Citation(chunk_id="c1", quote="ácidos y bases por separado"),
        Citation(chunk_id="c2", quote="Usar guantes y gafas"),
    ],
)


async def _search(session: object, query: str, k: int = 10) -> list[Hit]:
    return _HITS[:k]


async def _session() -> AsyncIterator[object]:
    yield object()


class _Traces:
    """Sesión falsa que acumula las trazas insertadas por el endpoint."""

    def __init__(self) -> None:
        self.items: list[ChatTrace] = []

    def __call__(self) -> "_Traces":
        return self

    async def __aenter__(self) -> "_Traces":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    def add(self, trace: ChatTrace) -> None:
        self.items.append(trace)

    async def commit(self) -> None:
        return None


def _gemini(answer: Answer) -> type:
    class _Fake:
        def __init__(self, **_: object) -> None: ...

        async def complete(self, prompt: str, schema: type[object]) -> Answer:
            return answer

    return _Fake


_Client = tuple[TestClient, _Traces]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Client]:
    chat.limiter.reset()
    app.dependency_overrides[get_session] = _session
    traces = _Traces()
    settings = SimpleNamespace(gemini_api_key=SecretStr("test-key"), gemini_model="test-model")
    monkeypatch.setattr(chat, "search", _search)
    monkeypatch.setattr(chat, "get_settings", lambda: settings)
    monkeypatch.setattr(chat, "GeminiClient", _gemini(_ANSWER))
    monkeypatch.setattr(chat, "get_sessionmaker", lambda: traces)
    yield TestClient(app), traces
    app.dependency_overrides.clear()


def test_chat_streaming_exitoso(client: _Client) -> None:
    http, traces = client

    response = http.post("/chat", json=_QUESTION)

    text = response.text
    assert response.status_code == 200
    assert text.index("event: citations") < text.index("event: answer")
    assert text.index("event: answer") < text.index("event: done")
    assert traces.items[0].citation_ids == ["c1", "c2"]
    assert traces.items[0].answer == _ANSWER.answer


def test_chat_cita_invalida_devuelve_error(
    client: _Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    http, _ = client
    invalida = Answer(
        answer="Dato inventado.",
        citations=[Citation(chunk_id="c1", quote="frase inexistente")],
    )
    monkeypatch.setattr(chat, "GeminiClient", _gemini(invalida))

    text = http.post("/chat", json=_QUESTION).text

    assert "event: error" in text
    assert "event: answer" not in text
    assert "citation_rejected" in text
    assert "unverifiable_quote" in text


def test_chat_rate_limit(client: _Client) -> None:
    http, _ = client

    for _ in range(10):
        assert http.post("/chat", json=_QUESTION).status_code == 200
    response = http.post("/chat", json=_QUESTION)

    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    assert response.headers["content-type"].startswith("application/problem+json")


def test_chat_cors_estricto(client: _Client) -> None:
    http, _ = client

    ajeno = http.post("/chat", json=_QUESTION, headers={"Origin": "http://evil.com"})
    propio = http.post("/chat", json=_QUESTION, headers={"Origin": "http://localhost:5173"})

    assert "access-control-allow-origin" not in ajeno.headers
    assert propio.headers["access-control-allow-origin"] == "http://localhost:5173"
