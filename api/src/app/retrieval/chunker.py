"""Troceo de textos normativos por artículo y numeral."""

import re
from typing import NamedTuple

MAX_ARTICLE_CHARS = 2000

_ORDEN = (
    "primero|segundo|tercero|cuarto|quinto|sexto|séptimo|sétimo|octavo|noveno|décimo|"
    "undécimo|duodécimo|decimoprimero|decimosegundo"
)
_ARTICLE_RE = re.compile(
    rf"^[ \t]*Art[íi]culo[ \t]+(?:\d{{1,3}}[ \t]*°?|(?:{_ORDEN}))(?=[\s.:;]|$)",
    re.IGNORECASE | re.MULTILINE,
)
_NUMERAL_RE = re.compile(r"^(?P<marker>\d{1,2}[.)]|[a-z]\))[ \t]*", re.IGNORECASE | re.MULTILINE)


class ChunkDraft(NamedTuple):
    """Trozo de norma listo para persistir, sin embedding."""

    article: str
    numeral: str | None
    text: str
    url: str


def split_by_article(raw_text: str, url: str) -> list[ChunkDraft]:
    """Divide el texto por artículo y subdivide los que superan el máximo."""
    headers = list(_ARTICLE_RE.finditer(raw_text))
    drafts: list[ChunkDraft] = []
    for position, match in enumerate(headers):
        end = headers[position + 1].start() if position + 1 < len(headers) else len(raw_text)
        block = raw_text[match.start() : end].strip()
        if block:
            drafts.extend(_split_block(match.group(0).strip(), block, url))
    return drafts


def _split_block(article: str, block: str, url: str) -> list[ChunkDraft]:
    if len(block) <= MAX_ARTICLE_CHARS:
        return [ChunkDraft(article, None, block, url)]
    numerals = _split_by_numeral(block)
    if len(numerals) > 1:
        return [ChunkDraft(article, marker, text, url) for marker, text in numerals]
    paragraphs = [part.strip() for part in block.split("\n\n") if part.strip()]
    if len(paragraphs) > 1:
        first = f"{paragraphs[0]}\n\n{paragraphs[1]}"
        return [ChunkDraft(article, None, first, url)] + [
            ChunkDraft(article, None, part, url) for part in paragraphs[2:]
        ]
    return [ChunkDraft(article, None, block, url)]


def _split_by_numeral(block: str) -> list[tuple[str, str]]:
    marks = list(_NUMERAL_RE.finditer(block))
    if len(marks) < 2:
        return []
    prefix = block[: marks[0].start()].strip()
    segments: list[tuple[str, str]] = []
    for position, mark in enumerate(marks):
        end = marks[position + 1].start() if position + 1 < len(marks) else len(block)
        body = block[mark.start() : end].strip()
        if not body:
            continue
        if position == 0 and prefix:
            body = f"{prefix}\n{body}"
        segments.append((mark.group("marker").strip(), body))
    return segments
