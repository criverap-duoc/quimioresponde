import pytest

from app.llm.embeddings import EmbeddingClient, EmbeddingDimensionError, ensure_dimensions

_KEY = "test-key"
_MODEL = "gemini-embedding-001"


def test_client_is_created_without_network() -> None:
    client = EmbeddingClient(api_key=_KEY, model=_MODEL)

    assert isinstance(client, EmbeddingClient)


async def test_embed_without_texts_returns_empty_list() -> None:
    client = EmbeddingClient(api_key=_KEY, model=_MODEL)

    assert await client.embed([]) == []


def test_ensure_dimensions_rejects_other_than_768() -> None:
    with pytest.raises(EmbeddingDimensionError) as error:
        ensure_dimensions([[0.0] * 767])

    assert error.value.expected == 768
    assert error.value.received == 767
    assert ensure_dimensions([[0.0] * 768]) == [[0.0] * 768]
