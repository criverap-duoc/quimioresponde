"""Esquema de respuesta estructurada del LLM."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    """Referencia literal a un chunk recuperado."""

    chunk_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class Answer(BaseModel):
    """Respuesta con la fuente de evidencia declarada y sus citas.

    `evidence_source` declara de dónde sale la respuesta:
    - `regulation`: fragmentos de `search_regulation`; exige citas literales.
    - `inventory`: inventario de ChemLab; no admite citas normativas.
    - `pubchem`: ficha de PubChem; no admite citas normativas.
    - `compatibility`: motor determinista de reglas; no admite citas normativas.
    - `none`: rechazo sin evidencia; exige `refusal_reason` no vacío.
    """

    model_config = ConfigDict(extra="forbid")

    answer: str
    citations: list[Citation]
    refusal_reason: str | None = None
    evidence_source: Literal["regulation", "inventory", "pubchem", "compatibility", "none"]
