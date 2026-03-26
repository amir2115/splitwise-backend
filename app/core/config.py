from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

from pydantic import field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CORS_ALLOW_ORIGINS = [
    "https://splitwise.ir",
    "https://www.splitwise.ir",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


class Settings(BaseSettings):
    app_name: str = "OfflineSplitwise Backend"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/offline_splitwise"
    jwt_secret_key: str = "change-me"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 14
    app_min_supported_version_code: Optional[int] = None
    app_latest_version_code: Optional[int] = None
    app_update_mode: str = "none"
    app_update_store_url: Optional[str] = None
    app_update_bazaar_store_url: Optional[str] = None
    app_update_myket_store_url: Optional[str] = None
    app_update_organic_store_url: Optional[str] = None
    app_update_title: Optional[str] = None
    app_update_message: Optional[str] = None
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://") and "+psycopg" not in value:
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @field_validator("cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def normalize_list_settings(cls, value: Union[str, List[str]]) -> Union[str, List[str]]:
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            return []
        if value.startswith("["):
            return value
        return [item.strip() for item in value.split(",") if item.strip()]

    @field_validator("app_update_mode", mode="before")
    @classmethod
    def normalize_update_mode(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip().lower()
        if normalized in {"", "none"}:
            return "none"
        if normalized not in {"soft", "hard"}:
            raise ValueError("APP_UPDATE_MODE must be one of: none, soft, hard")
        return normalized

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
