import pytest

from app.retrieval.search import rrf_fuse


def test_rrf_ordena_por_consenso() -> None:
    fused = rrf_fuse([["a", "b", "c"], ["b", "a", "d"]])
    scores = dict(fused)

    assert [chunk_id for chunk_id, _ in fused[:2]] == ["a", "b"]
    assert {chunk_id for chunk_id, _ in fused[2:]} == {"c", "d"}
    assert scores["a"] > scores["c"]
    assert scores["b"] > scores["d"]


def test_rrf_sin_duplicados() -> None:
    fused = rrf_fuse([["a", "a", "a"], ["b"]])

    assert sorted(chunk_id for chunk_id, _ in fused) == ["a", "b"]


def test_rrf_lista_vacia() -> None:
    fused = rrf_fuse([[], ["a", "b"]])

    assert [chunk_id for chunk_id, _ in fused] == ["a", "b"]
    assert fused[0][1] == pytest.approx(1 / (60 + 1))
    assert fused[1][1] == pytest.approx(1 / (60 + 2))


def test_rrf_empate_estable() -> None:
    fused = rrf_fuse([["a", "b"], ["b", "a"]])

    assert [chunk_id for chunk_id, _ in fused] == ["a", "b"]
    assert fused[0][1] == pytest.approx(fused[1][1])
