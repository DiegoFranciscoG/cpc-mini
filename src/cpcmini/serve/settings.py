"""Configuración de la API por variables de entorno (sin valores por defecto para lo crítico)."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CPCMINI_", extra="ignore")

    # Obligatorias: si faltan, la API no arranca.
    database_url: str
    model_dir: str
    cors_allowed_origins: str

    config_dir: str = "configs"
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10_000)
    max_body_bytes: int = Field(default=16_384, ge=1_024, le=1_048_576)
    docs_enabled: bool = True
    trust_proxy_headers: bool = False

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard(cls, value: str) -> str:
        origins = [o.strip() for o in value.split(",") if o.strip()]
        if not origins or any(o == "*" for o in origins):
            raise ValueError(
                "CPCMINI_CORS_ALLOWED_ORIGINS debe listar orígenes explícitos, sin '*'"
            )
        return value

    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]
