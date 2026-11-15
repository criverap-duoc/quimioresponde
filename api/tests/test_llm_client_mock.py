from types import SimpleNamespace
from typing import Any

import pytest
from google import genai

from app.llm.client import GeminiClient, LLMResponseError
from app.llm.schemas import Answer

_MODEL = "gemini-2.5-flash"


class _FakeModels:
    def __init__(self, response: Any) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    async def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, response: Any) -> None:
        self.models = _FakeModels(response)
        self.aio = SimpleNamespace(models=self.models)


def _fake_genai(monkeypatch: pytest.MonkeyPatch, response: Any) -> _FakeClient:
    fake = _FakeClient(response)
    monkeypatch.setattr(genai, "Client", lambda **kwargs: fake)
    return fake


async def test_gemini_client_parsea_respuesta(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = Answer(answer="hola", citations=[], refusal_reason="prueba")
    fake = _fake_genai(monkeypatch, SimpleNamespace(parsed=answer, text=answer.model_dump_json()))
    client = GeminiClient(api_key="test-key", model=_MODEL)

    assert await client.complete("prompt", Answer) is answer
    call = fake.models.calls[0]
    assert call["config"].response_mime_type == "application/json"
    assert "answer" in call["config"].response_schema["properties"]


async def test_gemini_client_respuesta_invalida_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_genai(monkeypatch, SimpleNamespace(parsed=None, text="x" * 900))
    client = GeminiClient(api_key="test-key", model=_MODEL)

    with pytest.raises(LLMResponseError) as excinfo:
        await client.complete("prompt", Answer)

    assert str(excinfo.value).count("x") == 500
