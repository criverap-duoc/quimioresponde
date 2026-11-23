"""Compatibilidad de almacenamiento como herramienta: envuelve el motor YAML."""

from app.rules.engine import check_compatibility
from app.tools.schemas import CheckStorageCompatibilityInput, CheckStorageCompatibilityOutput


async def check_storage_compatibility(
    inp: CheckStorageCompatibilityInput,
) -> CheckStorageCompatibilityOutput:
    """Evalúa cada par con reglas deterministas; el LLM solo explicará el resultado."""
    return CheckStorageCompatibilityOutput(result=check_compatibility(inp.items))
