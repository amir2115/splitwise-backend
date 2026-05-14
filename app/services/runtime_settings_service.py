from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.domain import AppSetting

RUNTIME_SETTING_KEYS = {
    "phone_verification_required",
    "sms_ir_api_key",
    "sms_ir_verify_template_id",
    "sms_ir_verify_template_id_android",
    "sms_ir_verify_parameter_name",
    "sms_otp_bypass_enabled",
    "sms_ir_invited_account_template_id",
    "sms_ir_invited_account_link_parameter_name",
    "sms_ir_invited_account_group_name_parameter_name",
    "web_app_base_url",
    "support_email",
    "support_url",
    "twitter_url",
    "instagram_url",
    "telegram_url",
    "linkedin_url",
    "enamad_url",
    "pwa_url",
    "bazaar_url",
    "myket_url",
    "apk_url",
    "footer_short_text",
    "contact_body",
}

PUBLIC_SITE_SETTING_KEYS = {
    "support_email",
    "support_url",
    "twitter_url",
    "instagram_url",
    "telegram_url",
    "linkedin_url",
    "enamad_url",
    "pwa_url",
    "bazaar_url",
    "myket_url",
    "apk_url",
    "footer_short_text",
    "contact_body",
}

PUBLIC_SITE_SETTING_DEFAULTS: dict[str, str | None] = {
    "support_email": "support@splitwise.ir",
    "support_url": "mailto:support@splitwise.ir",
    "twitter_url": None,
    "instagram_url": None,
    "telegram_url": None,
    "linkedin_url": None,
    "enamad_url": "https://trustseal.enamad.ir/?id=718689&Code=COXTxN1QUVKAtLC9KVXyUWwWocPt9drz",
    "pwa_url": "https://pwa.splitwise.ir",
    "bazaar_url": "https://cafebazaar.ir/app/com.encer.offlinesplitwise",
    "myket_url": "https://myket.ir/app/com.encer.offlinesplitwise",
    "apk_url": "https://splitwise.ir/files/app.apk",
    "footer_short_text": "مدیریت هزینه‌های گروهی، ساده و شفاف.",
    "contact_body": "برای پشتیبانی، پیشنهاد یا پیگیری موضوعات مربوط به دنگینو از ایمیل پشتیبانی استفاده کنید.",
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
    configured = getattr(settings, key, None)
    if configured is not None:
        return configured
    return PUBLIC_SITE_SETTING_DEFAULTS.get(key)


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


def list_public_site_settings(db: Session) -> dict[str, str | None]:
    return {key: get_runtime_setting(db, key) for key in sorted(PUBLIC_SITE_SETTING_KEYS)}
