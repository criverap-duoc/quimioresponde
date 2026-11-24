"""Endpoint /chat: streaming SSE, rechazo de citas, rate limit y CORS."""

from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient

from app.agent.state import AgentState
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
    evidence_source="regulation",
)


def _state(
    answer: Answer, hits: list[Hit], tools: tuple[str, ...] = ("search_regulation",)
) -> AgentState:
    return AgentState(
        messages=[{"role": "user", "content": "?"}],
        steps=1,
        tools_called=list(tools),
        hits=hits,
        decision=None,
        final_answer=answer,
    )


def _agent(
    answer: Answer, hits: list[Hit], tools: tuple[str, ...] = ("search_regulation",)
) -> object:
    async def _run(question: str, session: object) -> AgentState:
        return _state(answer, hits, tools)

    return _run


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


_Client = tuple[TestClient, _Traces]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Client]:
    chat.limiter.reset()
    app.dependency_overrides[get_session] = _session
    traces = _Traces()
    monkeypatch.setattr(chat, "run_agent", _agent(_ANSWER, _HITS))
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
    assert '"tools_called": ["search_regulation"]' in text.split("event: done", 1)[1]
    assert traces.items[0].citation_ids == ["c1", "c2"]
    assert traces.items[0].answer == _ANSWER.answer
    assert traces.items[0].tools_called == ["search_regulation"]


def test_chat_cita_invalida_devuelve_error(
    client: _Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    http, _ = client
    invalida = Answer(
        answer="Dato inventado.",
        citations=[Citation(chunk_id="c1", quote="frase inexistente")],
        evidence_source="regulation",
    )
    monkeypatch.setattr(chat, "run_agent", _agent(invalida, _HITS))

    text = http.post("/chat", json=_QUESTION).text

    assert "event: error" in text
    assert "event: answer" not in text
    assert "citation_rejected" in text
    assert "unverifiable_quote" in text


def test_chat_respuesta_de_inventario_sin_citas(
    client: _Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    http, traces = client
    inventario = Answer(
        answer="No hay reactivos vencidos en el inventario.",
        citations=[],
        evidence_source="inventory",
    )
    monkeypatch.setattr(chat, "run_agent", _agent(inventario, [], tools=("get_inventory",)))

    text = http.post("/chat", json=_QUESTION).text

    assert "event: answer" in text
    assert "citation_rejected" not in text
    assert traces.items[0].citation_ids == []
    assert traces.items[0].tools_called == ["get_inventory"]


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
