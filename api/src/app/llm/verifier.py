"""Verificación determinista de la respuesta según la evidencia declarada."""

import re
from enum import StrEnum

from app.llm.schemas import Answer
from app.retrieval.search import Hit

_WHITESPACE = re.compile(r"\s+")
_TOOL_SOURCES = frozenset({"inventory", "pubchem", "compatibility"})


class CitationRejection(StrEnum):
    """Motivos por los que una respuesta se rechaza."""

    NO_CITATIONS = "no_citations"
    UNVERIFIABLE_QUOTE = "unverifiable_quote"
    UNKNOWN_CHUNK = "unknown_chunk"
    REFUSAL_WITH_CITATIONS = "refusal_with_citations"
    CITATIONS_NOT_ALLOWED = "citations_not_allowed"


class CitationRejected(Exception):
    """La respuesta incumple las reglas de evidencia y no debe entregarse."""

    def __init__(self, reason: CitationRejection) -> None:
        super().__init__(reason.value)
        self.reason = reason


def verify(answer: Answer, hits: list[Hit]) -> None:
    """Verifica la respuesta según su `evidence_source` declarado."""
    if answer.evidence_source == "regulation":
        _verify_regulation(answer, hits)
    elif answer.evidence_source in _TOOL_SOURCES:
        if answer.citations:
            raise CitationRejected(CitationRejection.CITATIONS_NOT_ALLOWED)
        if answer.refusal_reason is not None:
            raise CitationRejected(CitationRejection.REFUSAL_WITH_CITATIONS)
    elif answer.citations or not answer.refusal_reason:
        raise CitationRejected(CitationRejection.NO_CITATIONS)


def _verify_regulation(answer: Answer, hits: list[Hit]) -> None:
    """Exige citas literales de los chunks recuperados, sin rechazo simultáneo."""
    if not answer.citations:
        if answer.refusal_reason is None:
            raise CitationRejected(CitationRejection.NO_CITATIONS)
        return
    if answer.refusal_reason is not None:
        raise CitationRejected(CitationRejection.REFUSAL_WITH_CITATIONS)
    texts = {hit.chunk_id: _normalize(hit.text) for hit in hits}
    for citation in answer.citations:
        if citation.chunk_id not in texts:
            raise CitationRejected(CitationRejection.UNKNOWN_CHUNK)
        if _normalize(citation.quote) not in texts[citation.chunk_id]:
            raise CitationRejected(CitationRejection.UNVERIFIABLE_QUOTE)


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()
