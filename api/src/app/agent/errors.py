"""Errores del agente que el endpoint traduce a `problem+json`."""


class AgentError(Exception):
    """Fallo del agente: nunca se entrega como respuesta al usuario."""


class AgentStepLimitError(AgentError):
    """El agente agotó los pasos sin producir una respuesta final."""

    def __init__(self, max_steps: int) -> None:
        super().__init__(f"límite de {max_steps} pasos alcanzado sin respuesta final")


class AgentNoAnswer(AgentError):
    """El grafo terminó sin respuesta final por una ruta inesperada."""
