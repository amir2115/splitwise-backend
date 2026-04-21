from typing import Annotated
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Union

from pydantic import field_validator

from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CORS_ALLOW_ORIGINS = [
    "https://splitwise.ir",
    "https://www.splitwise.ir",
    "https://pwa.splitwise.ir",
    "https://panel.splitwise.ir",
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
    app_download_admin_secret: Optional[str] = None
    app_download_upload_dir: str = "/files"
    app_download_public_base_url: str = "https://api.splitwise.ir"
    admin_panel_username: Optional[str] = None
    admin_panel_password: Optional[str] = None
    admin_panel_password_hash: Optional[str] = None
    admin_panel_jwt_secret: Optional[str] = None
    admin_panel_access_token_expire_minutes: int = 480
    admin_panel_rate_limit_attempts: int = 5
    admin_panel_rate_limit_window_minutes: int = 10
    admin_panel_rate_limit_lockout_minutes: int = 15
    sms_ir_api_key: Optional[str] = None
    sms_ir_verify_template_id: Optional[int] = None
    sms_ir_verify_parameter_name: str = "OTP"
    sms_ir_invited_account_template_id: Optional[int] = None
    sms_ir_invited_account_link_parameter_name: str = "TOKEN"
    sms_ir_invited_account_group_name_parameter_name: str = "GROUP_NAME"
    web_app_base_url: Optional[str] = None
    phone_verification_code_length: int = 5
    phone_verification_ttl_seconds: int = 120
    phone_verification_resend_cooldown_seconds: int = 60
    phone_verification_max_verify_attempts: int = 5
    phone_verification_max_send_attempts_per_window: int = 3
    cors_allow_origins: Annotated[List[str], NoDecode] = DEFAULT_CORS_ALLOW_ORIGINS.copy()
    cors_allow_origin_regex: Optional[str] = r"^https://([a-z0-9-]+\.)?splitwise\.ir$|^http://(localhost|127\.0\.0\.1)(:\d+)?$"
    cors_allow_credentials: bool = True
    cors_allow_methods: Annotated[List[str], NoDecode] = ["*"]
    cors_allow_headers: Annotated[List[str], NoDecode] = ["*"]

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

    @field_validator("cors_allow_origins", "cors_allow_methods", "cors_allow_headers", mode="before")
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

    @field_validator("cors_allow_origins", mode="after")
    @classmethod
    def normalize_cors_origins(cls, value: List[str]) -> List[str]:
        normalized: List[str] = []
        for item in value:
            origin = item.strip().rstrip("/")
            if origin and origin not in normalized:
                normalized.append(origin)
        return normalized

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

    @field_validator(
        "sms_ir_verify_parameter_name",
        "sms_ir_invited_account_link_parameter_name",
        "sms_ir_invited_account_group_name_parameter_name",
        mode="before",
    )
    @classmethod
    def normalize_sms_parameter_name(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip().strip("#").strip()
        if not normalized:
            raise ValueError("SMS_IR_VERIFY_PARAMETER_NAME must not be empty")
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
