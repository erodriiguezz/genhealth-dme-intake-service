from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

SERVICE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVICE_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://intake:intake@localhost:55433/intake"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    health_timeout_ms: int = 2000
    db_tcp_user_timeout_ms: int = 10000
    env: str = "development"
    jwt_secret: str = "dev-only-insecure-secret-change-me-0123456789"
    jwt_ttl_min: int = 60
    seed_users: str = ""

    @field_validator("database_url")
    @classmethod
    def normalize_driver(cls, v: str) -> str:
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix) :]
        return v

    @model_validator(mode="after")
    def require_real_secret_in_production(self) -> "Settings":
        if self.env == "production" and (
            len(self.jwt_secret) < 32 or self.jwt_secret.startswith("dev-only")
        ):
            raise ValueError("JWT_SECRET must be set to a random 32+ character value in production")
        return self

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip().rstrip("/") for o in v.split(",") if o.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
