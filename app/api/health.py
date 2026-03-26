from typing import Optional

from fastapi import APIRouter, Header

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()
settings = get_settings()


def resolve_store_url(app_store: Optional[str]) -> Optional[str]:
    normalized_store = (app_store or "").strip().lower()
    if normalized_store == "bazaar":
        return settings.app_update_bazaar_store_url or settings.app_update_store_url
    if normalized_store == "myket":
        return settings.app_update_myket_store_url or settings.app_update_store_url
    return settings.app_update_store_url


@router.get("/health", response_model=HealthResponse)
def health(x_app_store: Optional[str] = Header(default=None)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        min_supported_version_code=settings.app_min_supported_version_code,
        latest_version_code=settings.app_latest_version_code,
        update_mode=None if settings.app_update_mode == "none" else settings.app_update_mode,
        store_url=resolve_store_url(x_app_store),
        update_title=settings.app_update_title,
        update_message=settings.app_update_message,
    )
