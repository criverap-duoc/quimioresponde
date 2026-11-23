"""Recuperación normativa como herramienta: envuelve la búsqueda híbrida."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.retrieval import search as retrieval
from app.tools.schemas import HitOut, SearchRegulationInput, SearchRegulationOutput


async def search_regulation(
    inp: SearchRegulationInput, session: AsyncSession
) -> SearchRegulationOutput:
    """Recupera trozos normativos citables para una consulta en lenguaje natural."""
    hits = await retrieval.search(session, inp.query)
    return SearchRegulationOutput(
        hits=[
            HitOut(chunk_id=hit.chunk_id, article=hit.article, text=hit.text, url=hit.url)
            for hit in hits
        ]
    )
