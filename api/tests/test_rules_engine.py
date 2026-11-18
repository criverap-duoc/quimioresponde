"""Tests de tabla del motor determinista de compatibilidad química."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from app.rules.engine import check_compatibility

_FIXTURE = Path(__file__).parent / "fixtures" / "rules_cases.yaml"
_RULES_DIR = Path(__file__).parents[1] / "src" / "app" / "rules" / "data"
_CASES: list[dict[str, Any]] = yaml.safe_load(_FIXTURE.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", _CASES, ids=[case["id"] for case in _CASES])
def test_compatibilidad(case: dict[str, Any]) -> None:
    items = [(name, cas) for name, cas in case["items"]]
    result = check_compatibility(items)

    assert result.status == case["status"]
    assert result.summary
    if source := case.get("source"):
        assert all(source in match.source for match in result.rules)
    if result.rules:
        assert all(match.reason for match in result.rules)


def test_pares_sin_regla_se_marcan_unknown() -> None:
    result = check_compatibility([("Muestra A", None), ("Ácido nítrico", None)])

    assert result.status == "UNKNOWN"
    assert [match.severity for match in result.rules] == ["UNKNOWN"]
    assert result.rules[0].source == "sin regla"


def test_determinista() -> None:
    items = [("Ácido clorhídrico", None), ("Hidróxido de sodio", None), ("Acetona", None)]

    assert check_compatibility(items) == check_compatibility(items)


def test_reglas_decreto43_citan_articulo_17() -> None:
    raw = (_RULES_DIR / "decreto43_art17.yaml").read_text(encoding="utf-8")
    rules = yaml.safe_load(raw)["rules"]

    assert rules
    assert all("Art. 17" in rule["source"] for rule in rules)
