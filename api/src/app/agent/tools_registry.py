"""Registro cerrado de las cuatro herramientas: esquemas para el LLM y despacho."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, NamedTuple

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.check_storage_compatibility import check_storage_compatibility
from app.tools.get_chemical_info import get_chemical_info
from app.tools.get_inventory import get_inventory
from app.tools.schemas import (
    CheckStorageCompatibilityInput,
    GetChemicalInfoInput,
    GetInventoryInput,
    SearchRegulationInput,
)
from app.tools.search_regulation import search_regulation

Runner = Callable[[dict[str, Any], AsyncSession], Awaitable[BaseModel]]


class ToolNotFound(Exception):
    """El LLM pidió una herramienta fuera de la lista cerrada."""

    def __init__(self, name: str) -> None:
        super().__init__(f"herramienta no disponible: {name}")


class InvalidToolArgs(Exception):
    """Los argumentos no validan el contrato de la herramienta."""

    def __init__(self, name: str) -> None:
        super().__init__(f"argumentos inválidos para {name}")


class ToolArgs(BaseModel):
    """Argumentos que el LLM puede enviar: unión de las entradas de las cuatro herramientas."""

    model_config = ConfigDict(extra="forbid")

    query: str | None = None
    cas: str | None = None
    expiring_in_days: int | None = None
    expired: bool | None = None
    hazard_level: int | None = None
    location: str | None = None
    cas_number: str | None = None
    items: list[list[str]] | None = None


class ToolSpec(NamedTuple):
    """Herramienta expuesta: descripción para el LLM, esquema de entrada y ejecutor."""

    description: str
    input_model: type[BaseModel]
    run: Runner


async def _regulation(args: dict[str, Any], session: AsyncSession) -> BaseModel:
    return await search_regulation(SearchRegulationInput.model_validate(args), session)


async def _chemical(args: dict[str, Any], _: AsyncSession) -> BaseModel:
    return await get_chemical_info(GetChemicalInfoInput.model_validate(args))


async def _inventory(args: dict[str, Any], _: AsyncSession) -> BaseModel:
    return await get_inventory(GetInventoryInput.model_validate(args))


async def _compatibility(args: dict[str, Any], _: AsyncSession) -> BaseModel:
    return await check_storage_compatibility(CheckStorageCompatibilityInput.model_validate(args))


TOOLS: dict[str, ToolSpec] = {
    "search_regulation": ToolSpec(
        "Busca normativa chilena vigente (D.S. 43/2015, D.S. 594/1999) por texto libre y "
        "devuelve fragmentos citables con chunk_id.",
        SearchRegulationInput,
        _regulation,
    ),
    "get_chemical_info": ToolSpec(
        "Ficha de PubChem por número CAS: nombre, fórmula, peso molecular y pictogramas GHS.",
        GetChemicalInfoInput,
        _chemical,
    ),
    "get_inventory": ToolSpec(
        "Inventario real de ChemLab con filtros opcionales: vencimiento, peligrosidad, "
        "ubicación y CAS.",
        GetInventoryInput,
        _inventory,
    ),
    "check_storage_compatibility": ToolSpec(
        "Compatibilidad de almacenamiento calculada por el motor determinista de reglas; "
        "recibe pares [nombre, CAS].",
        CheckStorageCompatibilityInput,
        _compatibility,
    ),
}


def describe() -> str:
    """Lista las herramientas y su esquema de entrada para el prompt del LLM."""
    lines = []
    for name, spec in TOOLS.items():
        schema = json.dumps(spec.input_model.model_json_schema(), ensure_ascii=False)
        lines.append(f"- {name}: {spec.description} args={schema}")
    return "\n".join(lines)


async def invoke_tool(name: str, args: dict[str, Any], session: AsyncSession) -> BaseModel:
    """Única puerta de entrada a las herramientas desde el grafo."""
    spec = TOOLS.get(name)
    if spec is None:
        raise ToolNotFound(name)
    try:
        return await spec.run(args, session)
    except ValidationError as exc:
        raise InvalidToolArgs(name) from exc
