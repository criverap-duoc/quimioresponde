"""Tests de las herramientas del agente: sin red real y sin LLM."""

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

import app.tools.get_chemical_info as chemical_info
import app.tools.get_inventory as inventory
from app.retrieval import search as retrieval
from app.retrieval.search import Hit
from app.rules.engine import CompatibilityResult
from app.tools.check_storage_compatibility import check_storage_compatibility
from app.tools.schemas import (
    CheckStorageCompatibilityInput,
    GetChemicalInfoInput,
    GetChemicalInfoOutput,
    GetInventoryInput,
    HitOut,
    SearchRegulationInput,
    ToolError,
)
from app.tools.search_regulation import search_regulation

_ITEM = {
    "id": "3f1c2b7e-0000-4000-8000-000000000001",
    "name": "Ácido clorhídrico",
    "casNumber": "7647-01-0",
    "chemicalFormula": "HCl",
    "quantity": 500.0,
    "unit": "mL",
    "location": "Estante A1",
    "hazardLevel": 3,
    "expiryDate": "2027-01-01T00:00:00Z",
    "daysUntilExpiry": 40,
    "isExpired": False,
    "isLowStock": True,
}


def _response(payload: dict[str, Any], status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=payload, request=httpx.Request("GET", "https://test"))


@pytest.fixture(autouse=True)
def _clear_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chemical_info, "_CACHE", {})


@pytest.fixture
def chemlab(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SimpleNamespace(
        chemlab_base_url="https://chemlab.test/inventory",
        chemlab_api_key=SecretStr("clave-de-prueba"),
    )
    monkeypatch.setattr(inventory, "get_settings", lambda: settings)


def _pubchem(url: str) -> dict[str, Any]:
    """Respuestas mínimas de las tres consultas reales: CID, propiedades y GHS."""
    if url.endswith("/cids/JSON"):
        return {"IdentifierList": {"CID": [313]}}
    if "/property/" in url:
        props = {"CID": 313, "MolecularFormula": "ClH", "MolecularWeight": "36.46"}
        return {"PropertyTable": {"Properties": [props]}}
    icons = [
        {"Type": "Icon", "Extra": "Corrosive"},
        {"Type": "Icon", "Extra": "Corrosive"},
        {"Type": "Icon", "Extra": "Irritant"},
        {"Type": "Color", "Extra": "GHSDanger"},
    ]
    ghs = {
        "TOCHeading": "GHS Classification",
        "Information": [{"Value": {"StringWithMarkup": [{"String": "  ", "Markup": icons}]}}],
    }
    return {"Record": {"RecordTitle": "Hydrochloric Acid", "Section": [{"Section": [ghs]}]}}


async def test_search_regulation_mapea_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    hit = Hit(
        chunk_id="c1",
        document_id="d1",
        article="Art. 17",
        numeral="17.2",
        text="Texto",
        url="https://bcn",
        score=0.5,
    )

    async def fake_search(session: AsyncSession, query: str, k: int = 10) -> list[Hit]:
        return [hit]

    monkeypatch.setattr(retrieval, "search", fake_search)

    out = await search_regulation(SearchRegulationInput(query="ácidos"), cast(AsyncSession, None))

    assert out.hits == [HitOut(chunk_id="c1", article="Art. 17", text="Texto", url="https://bcn")]


async def test_get_chemical_info_parsea_pubchem(monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []

    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        urls.append(url)
        return _response(_pubchem(url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    out = await chemical_info.get_chemical_info(GetChemicalInfoInput(cas="7647-01-0"))

    assert [url.split("/rest/")[1].split("/")[0] for url in urls] == ["pug", "pug", "pug_view"]

    assert out.name == "Hydrochloric Acid"
    assert out.formula == "ClH"
    assert out.molecular_weight == pytest.approx(36.46)
    assert out.ghs_pictograms == ["Corrosive", "Irritant"]
    assert out.source == "pubchem"


async def test_get_chemical_info_falla_sin_lanzar(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("PubChem caído")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    out = await chemical_info.get_chemical_info(GetChemicalInfoInput(cas="50-00-0"))

    assert out == GetChemicalInfoOutput(
        name=None, formula=None, molecular_weight=None, ghs_pictograms=[], source="pubchem_error"
    )


async def test_get_inventory_filtra_y_parsea(
    monkeypatch: pytest.MonkeyPatch, chemlab: None
) -> None:
    calls: list[dict[str, Any]] = []

    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        calls.append({"url": url, **kwargs})
        payload = {"data": [_ITEM], "page": 1, "pageSize": 100, "totalCount": 1, "totalPages": 1}
        return _response(payload)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    out = await inventory.get_inventory(GetInventoryInput(expiring_in_days=365, hazard_level=3))

    assert calls[0]["url"] == "https://chemlab.test/inventory"
    assert calls[0]["headers"] == {"X-Api-Key": "clave-de-prueba"}
    assert calls[0]["params"] == {
        "expiringInDays": 365,
        "hazardLevel": 3,
        "page": 1,
        "pageSize": 100,
    }
    assert out.total == 1
    assert out.truncated is False
    item = out.items[0]
    assert (item.name, item.cas_number, item.is_low_stock) == (
        "Ácido clorhídrico",
        "7647-01-0",
        True,
    )
    assert item.expiry_date == datetime(2027, 1, 1, tzinfo=UTC)


async def test_get_inventory_corta_a_tres_paginas(
    monkeypatch: pytest.MonkeyPatch, chemlab: None
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        return _response({"data": [_ITEM] * 100, "totalCount": 350})

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    out = await inventory.get_inventory(GetInventoryInput())

    assert (len(out.items), out.total, out.truncated) == (300, 350, True)


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "chemlab_auth_failed"), (503, "chemlab_unavailable"), (500, "chemlab_error")],
)
async def test_get_inventory_errores_http(
    monkeypatch: pytest.MonkeyPatch, chemlab: None, status: int, code: str
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        return _response({"message": "fallo"}, status=status)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ToolError, match=code):
        await inventory.get_inventory(GetInventoryInput())


async def test_get_inventory_timeout(monkeypatch: pytest.MonkeyPatch, chemlab: None) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ReadTimeout("cold start")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ToolError, match="chemlab_timeout"):
        await inventory.get_inventory(GetInventoryInput())


async def test_check_storage_compatibility_usa_motor_real() -> None:
    items = [("Ácido clorhídrico", "7647-01-0"), ("Hidróxido de sodio", "1310-73-2")]

    out = await check_storage_compatibility(CheckStorageCompatibilityInput(items=items))

    assert isinstance(out.result, CompatibilityResult)
    assert out.result.status == "INCOMPATIBLE"
