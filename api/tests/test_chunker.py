from app.retrieval.chunker import split_by_article

_URL = "https://www.bcn.cl/leychile/navegar?idNorma=1000"

_TWO_ARTICLES = """\
Artículo 1°. Objeto.
La presente norma regula el almacenamiento de sustancias peligrosas.

Artículo 2°. Ámbito de aplicación.
Se aplica a todos los laboratorios químicos del país.
"""

_LONG_ARTICLE = "Artículo 5°. Obligaciones del empleador.\n" + "\n".join(
    f"{number}. Obligación {number}: " + "mantener registro " * 40 for number in range(1, 5)
)

_PARAGRAPH_ARTICLE = "Artículo 9°. Disposiciones.\n\n" + "\n\n".join(
    "texto extenso " * 100 for _ in range(3)
)


def test_split_by_article_returns_one_draft_per_article() -> None:
    drafts = split_by_article(_TWO_ARTICLES, _URL)

    assert len(drafts) == 2
    assert [draft.article for draft in drafts] == ["Artículo 1°", "Artículo 2°"]
    assert [draft.numeral for draft in drafts] == [None, None]
    assert "regula el almacenamiento" in drafts[0].text
    assert "laboratorios químicos" in drafts[1].text
    assert all(draft.url == _URL for draft in drafts)


def test_long_article_is_split_by_numeral_keeping_parent_article() -> None:
    drafts = split_by_article(_LONG_ARTICLE, _URL)

    assert len(drafts) == 4
    assert {draft.article for draft in drafts} == {"Artículo 5°"}
    assert [draft.numeral for draft in drafts] == ["1.", "2.", "3.", "4."]
    assert all(f"Obligación {index}" in draft.text for index, draft in enumerate(drafts, start=1))
    assert "Obligaciones del empleador" in drafts[0].text


def test_long_article_without_numerals_is_split_by_paragraphs() -> None:
    drafts = split_by_article(_PARAGRAPH_ARTICLE, _URL)

    assert len(drafts) == 3
    assert {draft.article for draft in drafts} == {"Artículo 9°"}
    assert all(draft.numeral is None for draft in drafts)
    assert "Disposiciones" in drafts[0].text
