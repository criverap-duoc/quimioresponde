"""Hashes de versión y claves de idempotencia para la ingesta."""

import hashlib


def version_hash(raw: bytes) -> str:
    """Devuelve el SHA-256 hexadecimal del contenido crudo."""
    return hashlib.sha256(raw).hexdigest()


def idempotency_key(norma: str, version_hash: str) -> str:
    """Compone la clave de idempotencia de una norma y su versión."""
    return f"{norma}:{version_hash}"
