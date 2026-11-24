import pytest

from app.llm.schemas import Answer, Citation
from app.llm.verifier import CitationRejected, CitationRejection, verify
from app.retrieval.search import Hit

_HITS = [
    Hit(
        chunk_id="c1",
        document_id="d1",
        article="Artículo 1",
        numeral=None,
        text="Almacenar ácidos y bases por separado en estanterías distinta.",
        url="https://example.test/decreto-43",
        score=0.9,
    ),
    Hit(
        chunk_id="c2",
        document_id="d1",
        article="Artículo 2",
        numeral="2.1",
        text="Usar guantes y gafas protectoras al manipular sustancias corrosivas.",
        url="https://example.test/decreto-43",
        score=0.8,
    ),
]


def test_acepta_citas_literales() -> None:
    answer = Answer(
        answer="Separar ácidos y bases y usar protección ocular.",
        citations=[
            Citation(chunk_id="c1", quote="ácidos y bases por separado"),
            Citation(chunk_id="c2", quote="Usar guantes y gafas protectoras"),
        ],
        evidence_source="regulation",
    )

    verify(answer, _HITS)


def test_acepta_quote_con_espacios_distintos() -> None:
    answer = Answer(
        answer="Separar ácidos y bases.",
        citations=[Citation(chunk_id="c1", quote="  Almacenar    ácidos   y bases por separado  ")],
        evidence_source="regulation",
    )

    verify(answer, _HITS)


def test_acepta_respuesta_de_inventario_sin_citas() -> None:
    answer = Answer(
        answer="No hay reactivos vencidos en el inventario.",
        citations=[],
        evidence_source="inventory",
    )

    verify(answer, [])


def test_acepta_rechazo_sin_evidencia() -> None:
    answer = Answer(
        answer="",
        citations=[],
        refusal_reason="no encontrado en el corpus",
        evidence_source="none",
    )

    verify(answer, [])


def test_rechaza_citas_en_respuesta_de_herramienta() -> None:
    answer = Answer(
        answer="No hay reactivos vencidos en el inventario.",
        citations=[Citation(chunk_id="c1", quote="ácidos y bases")],
        evidence_source="inventory",
    )

    with pytest.raises(CitationRejected) as excinfo:
        verify(answer, _HITS)

    assert excinfo.value.reason is CitationRejection.CITATIONS_NOT_ALLOWED


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        pytest.param(
            Answer(
                answer="No hay evidencia suficiente.",
                citations=[],
                evidence_source="regulation",
            ),
            CitationRejection.NO_CITATIONS,
            id="sin-citas",
        ),
        pytest.param(
            Answer(
                answer="Dato sin respaldo.",
                citations=[],
                evidence_source="none",
            ),
            CitationRejection.NO_CITATIONS,
            id="rechazo-sin-motivo",
        ),
        pytest.param(
            Answer(
                answer="Consulta fuera de alcance.",
                citations=[Citation(chunk_id="c1", quote="ácidos y bases")],
                refusal_reason="fuera de alcance",
                evidence_source="regulation",
            ),
            CitationRejection.REFUSAL_WITH_CITATIONS,
            id="rechazo-con-citas",
        ),
        pytest.param(
            Answer(
                answer="Dato inventado.",
                citations=[Citation(chunk_id="c9", quote="ácidos")],
                evidence_source="regulation",
            ),
            CitationRejection.UNKNOWN_CHUNK,
            id="chunk-desconocido",
        ),
        pytest.param(
            Answer(
                answer="Dato inventado.",
                citations=[Citation(chunk_id="c1", quote="frase")],
                evidence_source="regulation",
            ),
            CitationRejection.UNVERIFIABLE_QUOTE,
            id="quote-no-literal",
        ),
    ],
)
def test_rechaza(answer: Answer, reason: CitationRejection) -> None:
    with pytest.raises(CitationRejected) as excinfo:
        verify(answer, _HITS)

    assert excinfo.value.reason is reason
