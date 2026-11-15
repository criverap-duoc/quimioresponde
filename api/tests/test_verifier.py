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
    )

    verify(answer, _HITS)


def test_acepta_quote_con_espacios_distintos() -> None:
    answer = Answer(
        answer="Separar ácidos y bases.",
        citations=[Citation(chunk_id="c1", quote="  Almacenar    ácidos   y bases por separado  ")],
    )

    verify(answer, _HITS)


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        pytest.param(
            Answer(answer="No hay evidencia suficiente.", citations=[]),
            CitationRejection.NO_CITATIONS,
            id="sin-citas",
        ),
        pytest.param(
            Answer(
                answer="Consulta fuera de alcance.",
                citations=[Citation(chunk_id="c1", quote="ácidos y bases")],
                refusal_reason="fuera de alcance",
            ),
            CitationRejection.REFUSAL_WITH_CITATIONS,
            id="rechazo-con-citas",
        ),
        pytest.param(
            Answer(answer="Dato inventado.", citations=[Citation(chunk_id="c9", quote="ácidos")]),
            CitationRejection.UNKNOWN_CHUNK,
            id="chunk-desconocido",
        ),
        pytest.param(
            Answer(answer="Dato inventado.", citations=[Citation(chunk_id="c1", quote="frase")]),
            CitationRejection.UNVERIFIABLE_QUOTE,
            id="quote-no-literal",
        ),
    ],
)
def test_rechaza(answer: Answer, reason: CitationRejection) -> None:
    with pytest.raises(CitationRejected) as excinfo:
        verify(answer, _HITS)

    assert excinfo.value.reason is reason
