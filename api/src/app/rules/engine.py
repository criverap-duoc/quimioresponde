"""Motor determinista de compatibilidad química: reglas YAML, sin LLM.

Precedencia: D.S. 43/2015 (Art. 17) > OSHA/NFPA 400 > UNKNOWN. Sin aleatoriedad.
"""

from functools import cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from app.rules.families import ChemicalFamily, classify

Status = Literal["COMPATIBLE", "SEPARATE", "INCOMPATIBLE", "UNKNOWN"]

_DATA = Path(__file__).parent / "data"
_SOURCES = (_DATA / "decreto43_art17.yaml", _DATA / "osha_nfpa.yaml")
_RANK: dict[Status, int] = {"COMPATIBLE": 0, "SEPARATE": 1, "UNKNOWN": 2, "INCOMPATIBLE": 3}


class RuleMatch(BaseModel):
    """Regla aplicada a un par de sustancias, con severidad, motivo y fuente."""

    pair: tuple[str, str]
    severity: Status
    reason: str
    source: str


class CompatibilityResult(BaseModel):
    """Resultado agregado para la lista de sustancias evaluada."""

    status: Status
    rules: list[RuleMatch]
    summary: str


class _Rule(BaseModel):
    pair: tuple[ChemicalFamily, ChemicalFamily]
    severity: Status
    reason: str
    source: str


class _RuleSet(BaseModel):
    version: str
    source_url: str
    rules: list[_Rule]


@cache
def _index(path: Path) -> dict[tuple[str, str], _Rule]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {_key(*rule.pair): rule for rule in _RuleSet.model_validate(raw).rules}


def _key(first: str, second: str) -> tuple[str, str]:
    return (min(first, second), max(first, second))


def _unknown(first: ChemicalFamily, second: ChemicalFamily, reason: str) -> RuleMatch:
    return RuleMatch(
        pair=_key(first.value, second.value), severity="UNKNOWN", reason=reason, source="sin regla"
    )


def _pair_match(first: ChemicalFamily, second: ChemicalFamily) -> RuleMatch:
    if ChemicalFamily.INERT in (first, second):
        return _unknown(first, second, "Sustancia no clasificada: no se emite juicio.")
    key = _key(first.value, second.value)
    for path in _SOURCES:
        rule = _index(path).get(key)
        if rule is not None:
            return RuleMatch(
                pair=key, severity=rule.severity, reason=rule.reason, source=rule.source
            )
    return _unknown(first, second, "Sin regla en D.S. 43 ni en OSHA/NFPA.")


def _summary(matches: list[RuleMatch]) -> str:
    counts = {status: sum(match.severity == status for match in matches) for status in _RANK}
    detail = ", ".join(f"{total} {status.lower()}" for status, total in counts.items() if total)
    return f"{len(matches)} {'par' if len(matches) == 1 else 'pares'} evaluados: {detail}."


def check_compatibility(items: list[tuple[str, str | None]]) -> CompatibilityResult:
    """Evalúa cada par de la lista y agrega el resultado más severo."""
    families = [classify(name, cas) for name, cas in items]
    if len(families) < 2:
        return CompatibilityResult(
            status="COMPATIBLE", rules=[], summary="Menos de dos sustancias: nada que evaluar."
        )
    matches = [
        _pair_match(first, second)
        for position, first in enumerate(families)
        for second in families[position + 1 :]
    ]
    status = max((match.severity for match in matches), key=_RANK.__getitem__)
    return CompatibilityResult(status=status, rules=matches, summary=_summary(matches))
