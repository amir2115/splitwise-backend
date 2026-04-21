from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.domain import AppSetting

RUNTIME_SETTING_KEYS = {
    "sms_ir_api_key",
    "sms_ir_verify_template_id",
    "sms_ir_verify_parameter_name",
    "sms_ir_invited_account_template_id",
    "sms_ir_invited_account_link_parameter_name",
    "sms_ir_invited_account_group_name_parameter_name",
    "web_app_base_url",
}


def get_runtime_setting(db: Session, key: str) -> str | None:
    try:
        record = db.scalar(select(AppSetting).where(AppSetting.key == key))
        if record:
            value = record.value.strip()
            return value or None
    except SQLAlchemyError:
        pass
    settings = get_settings()
    return getattr(settings, key, None)


def get_runtime_setting_int(db: Session, key: str) -> int | None:
    value = get_runtime_setting(db, key)
    if value in (None, ""):
        return None
    return int(value)


def set_runtime_settings(db: Session, values: dict[str, str | None]) -> dict[str, str | None]:
    updated: dict[str, str | None] = {}
    for key, value in values.items():
        if key not in RUNTIME_SETTING_KEYS:
            continue
        existing = db.scalar(select(AppSetting).where(AppSetting.key == key))
        normalized = value.strip() if isinstance(value, str) else None
        if not normalized:
            if existing:
                db.delete(existing)
            updated[key] = None
            continue
        if existing:
            existing.value = normalized
        else:
            db.add(AppSetting(key=key, value=normalized))
        updated[key] = normalized
    db.commit()
    return updated


def list_runtime_settings(db: Session) -> dict[str, str | None]:
    return {key: get_runtime_setting(db, key) for key in sorted(RUNTIME_SETTING_KEYS)}
