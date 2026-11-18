import logging
import unicodedata
from enum import StrEnum


class ChemicalFamily(StrEnum):
    ACID = "ACID"
    BASE = "BASE"
    FLAMMABLE = "FLAMMABLE"
    OXIDIZER = "OXIDIZER"
    TOXIC = "TOXIC"
    WATER_REACTIVE = "WATER_REACTIVE"
    INERT = "INERT"


_KEYWORDS: dict[ChemicalFamily, str] = {
    ChemicalFamily.ACID: "acido",
    ChemicalFamily.BASE: "hidroxido|amoniaco|amoniacal|amina",
    ChemicalFamily.OXIDIZER: "peroxido|permanganato|dicromato|clorato|hipoclorito",
    ChemicalFamily.WATER_REACTIVE: "sodio metalico|potasio metalico|hidruro|carburo",
    ChemicalFamily.FLAMMABLE: "inflamable|acetona|etanol|metanol|hexano|tolueno|gasolina",
    ChemicalFamily.TOXIC: "cianuro|arsenico|mercurio|plomo|benceno|fosgeno",
}


def classify(name: str, cas: str | None = None) -> ChemicalFamily:
    """Clasifica por palabra clave en el nombre; el CAS se usará en Fase 3."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    for family, keywords in _KEYWORDS.items():
        if any(word in text for word in keywords.split("|")):
            return family
    logging.getLogger(__name__).warning("Familia química no reconocida: %r", name)
    return ChemicalFamily.INERT
