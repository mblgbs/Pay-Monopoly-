from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Pay Wallet API"
    app_env: Literal["dev", "test", "prod"] = "dev"
    port: int = 8007
    database_url: str = "sqlite:///./wallet.db"

    franceconnect_base_url: str = "http://127.0.0.1:8001"
    franceconnect_me_path: str = "/me"
    franceconnect_session_cookie_name: str = "fc_monopoly_session"

    services_monopoly_base_url: str = "http://127.0.0.1:8004"

    wallet_jwt_secret: str = "dev-wallet-secret-change-me"
    wallet_jwt_algorithm: str = "HS256"
    wallet_access_token_ttl_minutes: int = 120

    cors_origins_raw: str = Field(
        default="http://127.0.0.1:3002,http://localhost:3002",
        description="Comma separated origins",
    )

    stripe_webhook_shared_secret: str = "wallet-webhook-secret"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()

