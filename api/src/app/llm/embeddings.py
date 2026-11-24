"""Cliente asíncrono de embeddings sobre google-genai."""

import asyncio

import httpx
from google import genai
from google.genai import errors, types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.models.chunk import EMBEDDING_DIM

_BATCH_SIZE = 100
_BATCH_PAUSE_SECONDS = 0.6
_RETRYABLE = (errors.ServerError, httpx.TransportError)


def _is_retryable(exc: BaseException) -> bool:
    """Reintenta 5xx, transporte y 429; el resto de 4xx no se reintenta."""
    return isinstance(exc, _RETRYABLE) or (isinstance(exc, errors.ClientError) and exc.code == 429)


class EmbeddingError(Exception):
    """Falla al calcular embeddings."""


class EmbeddingDimensionError(EmbeddingError):
    """El vector devuelto no tiene la dimensión esperada."""

    def __init__(self, expected: int, received: int) -> None:
        super().__init__(f"dimensión inesperada: se esperaba {expected}, se recibió {received}")
        self.expected = expected
        self.received = received


def ensure_dimensions(vectors: list[list[float]]) -> list[list[float]]:
    """Valida que todos los vectores tengan la dimensión del corpus."""
    for vector in vectors:
        if len(vector) != EMBEDDING_DIM:
            raise EmbeddingDimensionError(EMBEDDING_DIM, len(vector))
    return vectors


class EmbeddingClient:
    """Genera embeddings en lotes de hasta 100 textos con reintentos acotados."""

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = genai.Client(api_key=api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Devuelve un vector por texto, respetando el orden de entrada."""
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            vectors.extend(await self._embed_batch(batch))
            if start + _BATCH_SIZE < len(texts):
                await asyncio.sleep(_BATCH_PAUSE_SECONDS)
        return vectors

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _embed_batch(self, batch: list[str]) -> list[list[float]]:
        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=batch,
            config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIM),
        )
        embeddings = response.embeddings or []
        if len(embeddings) != len(batch):
            raise EmbeddingError(
                f"se recibieron {len(embeddings)} embeddings para {len(batch)} textos"
            )
        return ensure_dimensions([embedding.values or [] for embedding in embeddings])
