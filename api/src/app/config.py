from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    gemini_api_key: SecretStr
    gemini_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    environment: Literal["local", "test", "staging", "production"] = "local"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cargada desde entorno y `.env`."""
    return Settings()
