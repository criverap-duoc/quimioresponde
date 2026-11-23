"""Contratos estrictos de las herramientas del agente y su error de fallo externo."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_pascal

from app.rules.engine import CompatibilityResult


class ToolError(Exception):
    """Fallo de una fuente externa; el agente decide cómo continuar."""


class _Strict(BaseModel):
    """Base de los contratos: rechaza campos desconocidos."""
    model_config = ConfigDict(extra="forbid")


class HitOut(_Strict):
    """Trozo normativo citable, sin la puntuación interna de la fusión."""
    chunk_id: str
    article: str
    text: str
    url: str


class SearchRegulationInput(_Strict):
    """Busca normativa vigente (D.S. 43, D.S. 594) por texto libre."""
    query: str = Field(min_length=1, max_length=500)


class SearchRegulationOutput(_Strict):
    """Trozos normativos recuperados, ordenados por relevancia."""
    hits: list[HitOut]


class GetChemicalInfoInput(_Strict):
    """Identificación y peligro GHS de una sustancia por su número CAS."""
    cas: str = Field(min_length=1, max_length=32)


class GetChemicalInfoOutput(_Strict):
    """Ficha resumida de PubChem; `source` indica el origen o el fallo."""
    name: str | None
    formula: str | None
    molecular_weight: float | None
    ghs_pictograms: list[str]
    source: str


class InventoryItem(_Strict):
    """Reactivo del inventario público de ChemLab (PublicReagentDto)."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=to_pascal)

    id: str
    name: str
    cas_number: str | None
    chemical_formula: str | None
    quantity: float
    unit: str
    location: str
    hazard_level: int
    expiry_date: datetime | None
    days_until_expiry: int | None
    is_expired: bool
    is_low_stock: bool


class GetInventoryInput(_Strict):
    """Consulta el inventario real de ChemLab con filtros opcionales."""
    expiring_in_days: int | None = Field(default=None, gt=0)
    expired: bool | None = None
    hazard_level: int | None = Field(default=None, ge=0, le=4)
    location: str | None = None
    cas_number: str | None = None


class GetInventoryOutput(_Strict):
    """Reactivos encontrados; `truncated` indica que hay más de los devueltos."""
    items: list[InventoryItem]
    total: int
    truncated: bool = False


class CheckStorageCompatibilityInput(_Strict):
    """Evalúa compatibilidad de almacenamiento para pares (nombre, CAS)."""
    items: list[tuple[str, str | None]]


class CheckStorageCompatibilityOutput(_Strict):
    """Resultado determinista del motor de reglas YAML."""
    result: CompatibilityResult
