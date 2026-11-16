"""Métricas deterministas de las evals offline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseResult:
    """Caso evaluado: lo esperado contra lo obtenido."""

    case_id: str
    category: str
    expected: str
    actual: str
    detail: str = ""

    @property
    def passed(self) -> bool:
        """El caso cumple exactamente lo esperado."""
        return self.expected == self.actual


def hit_at_k(predicted: list[str], expected: str, k: int) -> bool:
    """El chunk esperado está entre los primeros `k` resultados."""
    return expected in predicted[:k]


def refusal_correct(expected_reason: str | None, actual_reason: str | None) -> bool:
    """El motivo de rechazo coincide con el esperado."""
    return expected_reason == actual_reason


def citation_precision(cases: list[CaseResult]) -> float:
    """Proporción de casos de cita resueltos como se esperaba."""
    return _ratio(cases)


def summary(results: list[CaseResult]) -> dict[str, float]:
    """Agrega hit@5, exactitud de rechazos y precisión de citas."""
    return {
        "hit_at_5": _ratio(_by_category(results, "retrieval")),
        "refusal_accuracy": _ratio(_by_category(results, "refusal")),
        "citation_precision": citation_precision(_by_category(results, "citation")),
    }


def _by_category(results: list[CaseResult], category: str) -> list[CaseResult]:
    return [result for result in results if result.category == category]


def _ratio(cases: list[CaseResult]) -> float:
    if not cases:
        return 0.0
    return sum(1 for case in cases if case.passed) / len(cases)
