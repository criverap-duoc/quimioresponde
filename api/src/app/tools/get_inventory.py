"""Inventario real de ChemLab (solo lectura) como herramienta del agente."""

from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.config import get_settings
from app.tools.schemas import GetInventoryInput, GetInventoryOutput, InventoryItem, ToolError

_TIMEOUT = 45.0
_PAGE_SIZE = 100
_MAX_PAGES = 3
_QUERY_NAMES = {
    "expiring_in_days": "expiringInDays",
    "hazard_level": "hazardLevel",
    "cas_number": "casNumber",
}
_STATUS_ERRORS = {401: "chemlab_auth_failed", 503: "chemlab_unavailable"}


class _Page(BaseModel):
    """Página cruda del endpoint público: claves camelCase, resto se ignora."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    data: list[InventoryItem]
    total_count: int


async def get_inventory(inp: GetInventoryInput) -> GetInventoryOutput:
    """Consulta el inventario de ChemLab y pagina hasta 300 reactivos."""
    settings = get_settings()
    filters = {
        _QUERY_NAMES.get(key, key): value
        for key, value in inp.model_dump(exclude_none=True).items()
    }
    api_key = settings.chemlab_api_key.get_secret_value()
    items: list[InventoryItem] = []
    total = 0
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for page in range(1, _MAX_PAGES + 1):
            chunk = await _page(client, settings.chemlab_base_url, api_key, filters, page)
            total = chunk.total_count
            items.extend(chunk.data)
            if len(items) >= total or not chunk.data:
                break
    return GetInventoryOutput(items=items, total=total, truncated=len(items) < total)


async def _page(
    client: httpx.AsyncClient, url: str, api_key: str, filters: dict[str, Any], page: int
) -> _Page:
    try:
        response = await client.get(
            url,
            params={**filters, "page": page, "pageSize": _PAGE_SIZE},
            headers={"X-Api-Key": api_key},
        )
    except httpx.TimeoutException as exc:
        raise ToolError("chemlab_timeout") from exc
    except httpx.HTTPError as exc:
        raise ToolError("chemlab_unavailable") from exc
    if response.status_code != httpx.codes.OK:
        raise ToolError(_STATUS_ERRORS.get(response.status_code, "chemlab_error"))
    try:
        return _Page.model_validate(response.json())
    except ValueError as exc:
        raise ToolError("chemlab_error") from exc
