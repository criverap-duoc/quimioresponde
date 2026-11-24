"""Contrato entre el grafo y el LLM: decisión por paso y estado de la consulta."""

from typing import Literal, Self, TypedDict

from pydantic import BaseModel, ConfigDict, model_validator

from app.agent.tools_registry import ToolArgs
from app.llm.schemas import Answer
from app.retrieval.search import Hit


class AgentDecision(BaseModel):
    """Acción elegida por el LLM: llamar a una herramienta o responder ya."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["call_tool", "final_answer"]
    tool_name: str | None = None
    tool_args: ToolArgs | None = None
    answer: Answer | None = None

    @model_validator(mode="after")
    def _coherente(self) -> Self:
        """Exige la herramienta o la respuesta según la acción elegida."""
        if self.action == "call_tool" and not self.tool_name:
            raise ValueError("call_tool requiere tool_name")
        if self.action == "final_answer" and self.answer is None:
            raise ValueError("final_answer requiere answer")
        return self


class AgentState(TypedDict):
    """Estado de una consulta: conversación, pasos, evidencia y respuesta final."""

    messages: list[dict[str, str]]
    steps: int
    tools_called: list[str]
    hits: list[Hit]
    decision: AgentDecision | None
    final_answer: Answer | None
