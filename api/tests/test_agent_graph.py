"""Agente LangGraph: herramientas reales, límite de pasos y errores devueltos al LLM."""

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import tools_registry
from app.agent.errors import AgentStepLimitError
from app.agent.graph import run_agent
from app.agent.state import AgentDecision, AgentState
from app.agent.tools_registry import ToolArgs
from app.llm.schemas import Answer, Citation
from app.llm.verifier import verify
from app.tools.schemas import (
    GetInventoryInput,
    GetInventoryOutput,
    HitOut,
    SearchRegulationInput,
    SearchRegulationOutput,
)

_SESSION = AsyncSession()
_HIT = HitOut(
    chunk_id="c1",
    article="Artículo 1",
    text="Almacenar ácidos y bases por separado.",
    url="https://example.test/d43",
)
_ANSWER = Answer(
    answer="Separa ácidos y bases.",
    citations=[Citation(chunk_id="c1", quote="ácidos y bases por separado")],
    evidence_source="regulation",
)
_INVENTARIO = Answer(
    answer="No hay reactivos vencidos en el inventario.",
    citations=[],
    evidence_source="inventory",
)
_RECHAZO = Answer(
    answer="",
    citations=[],
    refusal_reason="El corpus no cubre la pregunta.",
    evidence_source="none",
)


class _Guion:
    """LLM de prueba: entrega las decisiones en orden y repite la última."""

    def __init__(self, *decisions: AgentDecision) -> None:
        self.decisions = list(decisions)
        self.prompts: list[str] = []

    async def complete(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        self.prompts.append(prompt)
        return self.decisions.pop(0) if len(self.decisions) > 1 else self.decisions[0]


def _tool(name: str, **args: object) -> AgentDecision:
    return AgentDecision(action="call_tool", tool_name=name, tool_args=ToolArgs(**args))


def _final(answer: Answer) -> AgentDecision:
    return AgentDecision(action="final_answer", answer=answer)


async def _fake_regulation(
    input: SearchRegulationInput, session: AsyncSession
) -> SearchRegulationOutput:
    return SearchRegulationOutput(hits=[_HIT])


async def _fake_inventory(input: GetInventoryInput) -> GetInventoryOutput:
    return GetInventoryOutput(items=[], total=0)


def _last_tool_message(state: AgentState) -> str:
    tool_messages = [message for message in state["messages"] if message["role"] == "tool"]
    return tool_messages[-1]["content"]


def test_decision_call_tool_sin_nombre_es_invalida() -> None:
    with pytest.raises(ValidationError):
        AgentDecision(action="call_tool")


async def test_agente_busca_evidencia_y_responde(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools_registry, "search_regulation", _fake_regulation)
    llm = _Guion(_tool("search_regulation", query="ácidos"), _final(_ANSWER))

    state = await run_agent("¿Cómo almaceno ácidos?", _SESSION, llm)

    assert state["tools_called"] == ["search_regulation"]
    assert state["final_answer"] == _ANSWER
    assert state["hits"][0].chunk_id == "c1"
    verify(_ANSWER, state["hits"])
    assert "Almacenar ácidos y bases" in llm.prompts[-1]
    assert "evidence_source" in llm.prompts[-1]


async def test_agente_consulta_inventario_sin_evidencia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools_registry, "get_inventory", _fake_inventory)
    llm = _Guion(_tool("get_inventory", expired=True), _final(_INVENTARIO))

    state = await run_agent("¿Qué reactivos están vencidos?", _SESSION, llm)

    assert state["tools_called"] == ["get_inventory"]
    assert state["hits"] == []
    verify(_INVENTARIO, state["hits"])
    assert '"total": 0' in _last_tool_message(state)
    assert _last_tool_message(state) in llm.prompts[-1]


async def test_agente_corta_al_agotar_los_pasos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools_registry, "search_regulation", _fake_regulation)
    llm = _Guion(_tool("search_regulation", query="ácidos"))

    with pytest.raises(AgentStepLimitError):
        await run_agent("¿Cómo almaceno ácidos?", _SESSION, llm)

    assert len(llm.prompts) == 6


async def test_agente_herramienta_desconocida_vuelve_al_llm() -> None:
    llm = _Guion(_tool("drop_tables"), _final(_RECHAZO))

    state = await run_agent("Borra todo.", _SESSION, llm)

    assert state["tools_called"] == ["drop_tables"]
    assert "herramienta no disponible: drop_tables" in _last_tool_message(state)


async def test_agente_argumentos_invalidos_vuelven_al_llm() -> None:
    llm = _Guion(_tool("get_inventory", expiring_in_days=-1), _final(_RECHAZO))

    state = await run_agent("¿Qué vence pronto?", _SESSION, llm)

    assert state["tools_called"] == ["get_inventory"]
    assert "argumentos inválidos para get_inventory" in _last_tool_message(state)
