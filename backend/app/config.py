"""Configuración central (12-factor: todo por variables de entorno)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos
    database_url: str = "postgresql+psycopg://yaku:yaku_dev_2026@localhost:5432/yakualerta"
    redis_url: str = "redis://localhost:6379/0"

    # Seguridad / JWT (RNF-05)
    jwt_secret: str = "cambia-esto-en-produccion"
    jwt_alg: str = "HS256"
    jwt_exp_min: int = 720

    # Mensajería (Twilio). Vacío => modo simulado para la demo.
    sms_modo: str = "simulado"
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from: str = ""
    whatsapp_from: str = ""

    # App
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    seed_demo: bool = True

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
