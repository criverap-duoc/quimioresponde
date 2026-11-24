"""Grafo LangGraph del agente: dos nodos, aristas explícitas y límite de pasos."""

from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.errors import AgentNoAnswer
from app.agent.nodes import agent_node, tools_node
from app.agent.state import AgentState
from app.config import get_settings
from app.llm.client import GeminiClient, LLMClient


def _next(state: AgentState) -> str:
    """Va a la herramienta si el LLM la pidió; en cualquier otro caso cierra el grafo."""
    decision = state["decision"]
    return "tools" if decision is not None and decision.action == "call_tool" else END


def _build(
    llm: LLMClient, session: AsyncSession
) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    """Compila el grafo sin checkpointer: cada consulta es independiente."""
    builder = StateGraph(AgentState)

    async def _agent(state: AgentState) -> AgentState:
        return await agent_node(state, llm)

    async def _tools(state: AgentState) -> AgentState:
        return await tools_node(state, session)

    builder.add_node("agent", _agent)
    builder.add_node("tools", _tools)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", _next, ["tools", END])
    builder.add_edge("tools", "agent")
    return builder.compile()


async def run_agent(
    question: str, session: AsyncSession, llm: LLMClient | None = None
) -> AgentState:
    """Ejecuta el grafo y devuelve el estado con `final_answer` ya resuelta."""
    graph = _build(llm or _gemini_client(), session)
    state = cast(AgentState, await graph.ainvoke(_initial(question)))
    if state["final_answer"] is None:
        raise AgentNoAnswer()
    return state


def _initial(question: str) -> AgentState:
    """Estado de una consulta nueva: sin pasos, sin evidencia y sin decisión."""
    return AgentState(
        messages=[{"role": "user", "content": question}],
        steps=0,
        tools_called=[],
        hits=[],
        decision=None,
        final_answer=None,
    )


def _gemini_client() -> LLMClient:
    """Cliente Gemini configurado por entorno."""
    settings = get_settings()
    return GeminiClient(
        api_key=settings.gemini_api_key.get_secret_value(), model=settings.gemini_model
    )
