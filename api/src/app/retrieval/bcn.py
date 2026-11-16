"""Descarga y troceo por artículo de normas publicadas en LeyChile (BCN)."""

import re
from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from app.retrieval.chunker import ChunkDraft, split_by_article

# La vista `navegar` de LeyChile es una SPA que carga el texto por JavaScript:
# la descarga directa no trae artículos. El XML de intercambio es público,
# estable y contiene la norma completa.
DECRETO_43_URL = "https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=1088802"
DECRETO_594_URL = "https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=167766"
USER_AGENT = "QuimioResponde/0.1 (+https://github.com/criverap-duoc/quimioresponde)"

_TIMEOUT = 60.0
_API_ROOT = Path(__file__).resolve().parents[3]
DECRETO_43_FIXTURE_PATH = _API_ROOT / "tests" / "fixtures" / "bcn_decreto43_articulo.html"
_URLS_POR_NORMA = {"decreto_43": DECRETO_43_URL, "decreto_594": DECRETO_594_URL}
_RUIDO = ("script", "style", "nav", "header", "footer", "aside")
_BINARIOS = ("ArchivoBinario",)
_ESPACIOS_RE = re.compile(r"[ \t\u00a0]+")
_SALTOS_RE = re.compile(r"\n{3,}")


class NormaFetchError(Exception):
    """La norma no se pudo descargar o robots.txt no lo permite."""


class NormaParseError(Exception):
    """El HTML descargado no contiene artículos reconocibles."""


async def fetch_norma(url: str) -> bytes:
    """Descarga el HTML de una norma respetando robots.txt."""
    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(
        timeout=_TIMEOUT, headers=headers, follow_redirects=True
    ) as client:
        if not await _robots_permite(client, url):
            raise NormaFetchError(f"robots.txt no permite descargar {url}")
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise NormaFetchError(f"No se pudo descargar {url}: {exc}") from exc
        return response.content


async def _robots_permite(client: httpx.AsyncClient, url: str) -> bool:
    try:
        response = await client.get(urljoin(url, "/robots.txt"))
    except httpx.HTTPError:
        return True
    if response.status_code >= 400:
        return True
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def parse_html(raw: bytes, norma: str, url: str) -> list[ChunkDraft]:
    """Extrae el texto útil de la respuesta de BCN y lo trocea por artículo."""
    texto = _texto_xml(raw) if _es_xml(raw) else _texto_html(raw)
    drafts = split_by_article(texto, url)
    if not drafts:
        raise NormaParseError(f"No se encontraron artículos en la norma {norma}")
    return drafts


def _es_xml(raw: bytes) -> bool:
    return raw.lstrip().startswith(b"<?xml")


def _texto_xml(raw: bytes) -> str:
    soup = BeautifulSoup(raw, "xml")
    for nodo in soup(list(_BINARIOS)):
        nodo.decompose()
    bloques = [nodo.get_text("\n", strip=True) for nodo in soup.find_all("Texto")]
    texto = "\n\n".join(bloque for bloque in bloques if bloque)
    return _SALTOS_RE.sub("\n\n", texto)


def _texto_html(raw: bytes) -> str:
    soup = BeautifulSoup(raw, "lxml")
    for tag in soup(list(_RUIDO)):
        tag.decompose()
    texto = _ESPACIOS_RE.sub(" ", soup.get_text("\n", strip=True))
    return _SALTOS_RE.sub("\n\n", texto)


def extraer_url_oficial(norma: str) -> str:
    """Devuelve la URL oficial en LeyChile para una norma conocida."""
    try:
        return _URLS_POR_NORMA[norma]
    except KeyError:
        raise ValueError(f"Norma desconocida: {norma}") from None


def cargar_fixture(norma: str) -> tuple[bytes, str]:
    """Devuelve el XML de prueba de BCN y su URL oficial para `decreto_43`."""
    if norma != "decreto_43":
        raise FileNotFoundError(
            f"fixture no disponible para {norma}; use la API real cuando la key esté activa"
        )
    return DECRETO_43_FIXTURE_PATH.read_bytes(), DECRETO_43_URL
