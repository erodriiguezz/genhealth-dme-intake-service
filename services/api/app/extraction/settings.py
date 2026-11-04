from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parent.parent.parent


class ExtractionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVICE_DIR / ".env", extra="ignore")

    extraction_provider: Literal["anthropic", "fake"] = "anthropic"
    extraction_model: str = "claude-opus-5-5"
    anthropic_api_key: SecretStr | None = None
    extraction_timeout_s: float = 110
    env: str = "development"


@lru_cache
def get_extraction_settings() -> ExtractionSettings:
    return ExtractionSettings()
