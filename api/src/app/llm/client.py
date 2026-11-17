"""Cliente LLM sobre google-genai con errores tipados."""

from typing import Any, Protocol

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

_MAX_RAW = 500


class LLMError(Exception):
    """Falla al obtener una respuesta del modelo."""


class LLMRateLimited(LLMError):
    """El proveedor limitó la tasa de solicitudes."""

    def __init__(self, retry_after: float | None = None) -> None:
        super().__init__("límite de tasa del LLM alcanzado")
        self.retry_after = retry_after


class LLMUnavailable(LLMError):
    """El proveedor no está disponible o falló la red."""


class LLMResponseError(LLMError):
    """El modelo no devolvió una respuesta que valide el esquema."""


class LLMClient(Protocol):
    """Interfaz de un cliente que produce respuestas estructuradas."""

    async def complete(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        """Devuelve una instancia de `schema` construida por el modelo."""
        ...


def _is_retryable(exc: BaseException) -> bool:
    """Solo 5xx del servidor y 429 son transitorios para la API."""
    if isinstance(exc, errors.ServerError):
        return True
    return isinstance(exc, errors.ClientError) and exc.code == 429


class GeminiClient:
    """Adaptador de Gemini con salida JSON validada por Pydantic."""

    def __init__(self, api_key: str, model: str) -> None:
        self._model = model
        self._client = genai.Client(api_key=api_key)

    async def complete(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        """Pide una respuesta JSON con `schema` y la devuelve ya parseada."""
        try:
            response = await self._generate(prompt, schema)
        except errors.APIError as exc:
            raise _translate(exc) from exc
        except httpx.TransportError as exc:
            raise LLMUnavailable("fallo de red al llamar al LLM") from exc
        if isinstance(response.parsed, schema):
            return response.parsed
        raw = response.text or ""
        try:
            return schema.model_validate_json(raw)
        except ValidationError as exc:
            raise LLMResponseError(f"respuesta no válida: {raw[:_MAX_RAW]}") from exc

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    async def _generate(
        self, prompt: str, schema: type[BaseModel]
    ) -> types.GenerateContentResponse:
        """Llama a Gemini; 5xx y 429 se reintentan, el resto de errores sube tal cual."""
        return await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_gemini_schema(schema),
            ),
        )


def _gemini_schema(model: type[BaseModel]) -> Any:
    """JSON Schema sin `additionalProperties`, que la API de Gemini no acepta."""
    return _strip_extras(model.model_json_schema())


def _strip_extras(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_extras(item) for key, item in value.items() if key != "additionalProperties"
        }
    if isinstance(value, list):
        return [_strip_extras(item) for item in value]
    return value


def _translate(exc: errors.APIError) -> LLMError:
    """Traduce un error HTTP del SDK al error tipado de la API."""
    if exc.code == 429:
        return LLMRateLimited(_retry_after(exc.response))
    if exc.code >= 500:
        return LLMUnavailable(f"el LLM devolvió {exc.code}")
    return LLMResponseError(f"el LLM rechazó la solicitud ({exc.code})")


def _retry_after(response: object) -> float | None:
    """Lee Retry-After en segundos; ignora fechas HTTP y valores inválidos."""
    if not isinstance(response, httpx.Response):
        return None
    raw = response.headers.get("retry-after")
    try:
        return float(raw) if raw is not None else None
    except ValueError:
        return None
