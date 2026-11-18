"""Motor determinista de compatibilidad química (reglas YAML, sin LLM)."""

from app.rules.engine import CompatibilityResult, RuleMatch, check_compatibility
from app.rules.families import ChemicalFamily, classify

__all__ = [
    "ChemicalFamily",
    "CompatibilityResult",
    "RuleMatch",
    "check_compatibility",
    "classify",
]
