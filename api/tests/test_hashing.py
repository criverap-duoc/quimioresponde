from app.retrieval.hashing import idempotency_key, version_hash


def test_version_hash_is_stable_and_distinguishes_content() -> None:
    raw = b"Decreto 43"

    assert version_hash(raw) == version_hash(b"Decreto 43")
    assert len(version_hash(raw)) == 64
    assert version_hash(raw) != version_hash(b"Decreto 594")


def test_version_hash_matches_known_sha256_vector() -> None:
    assert version_hash(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_idempotency_key_composes_norma_and_version() -> None:
    digest = version_hash(b"contenido")

    assert idempotency_key("Decreto 43", digest) == f"Decreto 43:{digest}"
