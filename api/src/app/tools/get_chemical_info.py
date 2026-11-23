"""Ficha química de PubChem (PUG REST + PUG-View) con caché en memoria por CAS."""

import time
from collections.abc import Iterator
from typing import Any
from urllib.parse import quote

import httpx

from app.tools.schemas import GetChemicalInfoInput, GetChemicalInfoOutput

_PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_PUG_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound"
_GHS = "GHS Classification"
_PROPERTIES = "MolecularFormula,MolecularWeight"
_TIMEOUT = 10.0
_TTL = 3600.0
_CACHE: dict[str, tuple[float, GetChemicalInfoOutput]] = {}


async def get_chemical_info(inp: GetChemicalInfoInput) -> GetChemicalInfoOutput:
    """Devuelve nombre, fórmula, peso molecular y pictogramas GHS del CAS consultado."""
    cas = inp.cas.strip()
    if cached := _cached(cas):
        return cached
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            result = await _lookup(client, cas)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return _error()
    _CACHE[cas] = (time.monotonic() + _TTL, result)
    return result


async def _lookup(client: httpx.AsyncClient, cas: str) -> GetChemicalInfoOutput:
    """PUG-View solo acepta números de registro: el CAS se resuelve a CID primero.

    Las propiedades van por PUG REST porque `heading` repetido en PUG-View se
    interpreta como ruta jerárquica y solo devuelve el primer nivel.
    """
    found = await client.get(f"{_PUG}/compound/name/{quote(cas, safe='')}/cids/JSON")
    found.raise_for_status()
    cid = found.json()["IdentifierList"]["CID"][0]
    props = await client.get(f"{_PUG}/compound/cid/{cid}/property/{_PROPERTIES}/JSON")
    props.raise_for_status()
    table = props.json()["PropertyTable"]["Properties"][0]
    view = await client.get(f"{_PUG_VIEW}/{cid}/JSON", params={"heading": _GHS})
    view.raise_for_status()
    record = view.json()["Record"]
    return GetChemicalInfoOutput(
        name=record.get("RecordTitle") or None,
        formula=table.get("MolecularFormula") or None,
        molecular_weight=_number(table.get("MolecularWeight")),
        ghs_pictograms=_pictograms(_section(record, _GHS)),
        source="pubchem",
    )


def _number(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _section(node: dict[str, Any], heading: str) -> dict[str, Any] | None:
    if node.get("TOCHeading") == heading:
        return node
    for child in node.get("Section", []):
        found = _section(child, heading)
        if found is not None:
            return found
    return None


def _values(node: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Recorre la información de una sección y de sus subsecciones."""
    for info in node.get("Information", []):
        yield info.get("Value", {})
    for child in node.get("Section", []):
        yield from _values(child)


def _markups(value: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Aplana los `Markup` anidados en cada `StringWithMarkup`."""
    for item in value.get("StringWithMarkup", []):
        yield from item.get("Markup", [])


def _pictograms(section: dict[str, Any] | None) -> list[str]:
    if section is None:
        return []
    names: list[str] = []
    for value in _values(section):
        for markup in _markups(value):
            name = markup.get("Extra")
            if markup.get("Type") == "Icon" and name and name not in names:
                names.append(str(name))
    return names


def _error() -> GetChemicalInfoOutput:
    return GetChemicalInfoOutput(
        name=None, formula=None, molecular_weight=None, ghs_pictograms=[], source="pubchem_error"
    )


def _cached(cas: str) -> GetChemicalInfoOutput | None:
    entry = _CACHE.get(cas)
    if entry is None or entry[0] <= time.monotonic():
        return None
    return entry[1]
