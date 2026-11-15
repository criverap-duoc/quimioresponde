"""Esquema de respuesta estructurada del LLM."""

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    """Referencia literal a un chunk recuperado."""

    chunk_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class Answer(BaseModel):
    """Respuesta con citas verificables o motivo explícito de rechazo."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[Citation]
    refusal_reason: str | None = None
