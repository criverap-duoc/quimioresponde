"""Verificación determinista de citas contra los chunks recuperados."""

import re
from enum import StrEnum

from app.llm.schemas import Answer
from app.retrieval.search import Hit

_WHITESPACE = re.compile(r"\s+")


class CitationRejection(StrEnum):
    """Motivos por los que una respuesta se rechaza."""

    NO_CITATIONS = "no_citations"
    UNVERIFIABLE_QUOTE = "unverifiable_quote"
    UNKNOWN_CHUNK = "unknown_chunk"
    REFUSAL_WITH_CITATIONS = "refusal_with_citations"


class CitationRejected(Exception):
    """La respuesta incumple las reglas de cita y no debe entregarse."""

    def __init__(self, reason: CitationRejection) -> None:
        super().__init__(reason.value)
        self.reason = reason


def verify(answer: Answer, hits: list[Hit]) -> None:
    """Rechaza respuestas sin citas o con citas que no son literales del chunk."""
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
