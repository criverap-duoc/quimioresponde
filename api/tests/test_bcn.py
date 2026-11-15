from pathlib import Path

import pytest

from app.retrieval.bcn import (
    DECRETO_43_URL,
    DECRETO_594_URL,
    NormaParseError,
    extraer_url_oficial,
    fetch_norma,
    parse_html,
)

_FIXTURE = Path(__file__).parent / "fixtures" / "bcn_decreto43_articulo.html"


def test_parse_html_extrae_articulos() -> None:
    drafts = parse_html(_FIXTURE.read_bytes(), "decreto_43", DECRETO_43_URL)

    assert len(drafts) >= 1
    assert all(draft.article for draft in drafts)
    assert all(draft.text for draft in drafts)
    assert all(draft.url == DECRETO_43_URL for draft in drafts)


def test_parse_html_sin_articulos_falla() -> None:
    with pytest.raises(NormaParseError, match="decreto_43"):
        parse_html(b"<html><body>Sin art\xc3\xadculos</body></html>", "decreto_43", DECRETO_43_URL)


def test_extraer_url_oficial() -> None:
    assert extraer_url_oficial("decreto_43") == DECRETO_43_URL
    assert extraer_url_oficial("decreto_594") == DECRETO_594_URL
    with pytest.raises(ValueError, match="decreto_999"):
        extraer_url_oficial("decreto_999")


@pytest.mark.integration
async def test_fetch_norma_real() -> None:
    raw = await fetch_norma(DECRETO_43_URL)

    assert raw
    assert parse_html(raw, "decreto_43", DECRETO_43_URL)
