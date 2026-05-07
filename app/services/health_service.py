from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.health import HealthResponse
from app.services.app_download_service import get_app_download_record
from app.services.admin_service import _parse_runtime_bool
from app.services.runtime_settings_service import get_runtime_setting

logger = logging.getLogger(__name__)


def resolve_store_url(
    app_store: Optional[str],
    *,
    bazaar_url: Optional[str],
    myket_url: Optional[str],
    direct_download_url: Optional[str],
) -> Optional[str]:
    normalized_store = (app_store or "").strip().lower()
    if normalized_store == "bazaar":
        candidates = (bazaar_url, direct_download_url, myket_url)
    elif normalized_store == "myket":
        candidates = (myket_url, direct_download_url, bazaar_url)
    else:
        candidates = (direct_download_url, bazaar_url, myket_url)

    for candidate in candidates:
        if candidate:
            return candidate
    return None


def build_health_response(db: Session, app_store: Optional[str]) -> HealthResponse:
    phone_verification_required = _parse_runtime_bool(get_runtime_setting(db, "phone_verification_required"))
    try:
        record = get_app_download_record(db)
    except SQLAlchemyError:
        # Health must stay up even during partial rollouts where the optional
        # app-download table or its connection state is temporarily unavailable.
        logger.exception("Failed to load app download health metadata")
        return HealthResponse(status="ok", phone_verification_required=phone_verification_required)

    if not record:
        return HealthResponse(status="ok", phone_verification_required=phone_verification_required)

    update_mode = None if record.update_mode in {None, "none"} else record.update_mode
    return HealthResponse(
        status="ok",
        phone_verification_required=phone_verification_required,
        min_supported_version_code=record.min_supported_version_code,
        latest_version_code=record.version_code,
        update_mode=update_mode,
        store_url=resolve_store_url(
            app_store,
            bazaar_url=record.bazaar_url,
            myket_url=record.myket_url,
            direct_download_url=record.direct_download_url,
        ),
        update_title=record.update_title,
        update_message=record.update_message,
    )
