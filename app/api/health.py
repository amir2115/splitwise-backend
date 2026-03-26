from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        min_supported_version_code=settings.app_min_supported_version_code,
        latest_version_code=settings.app_latest_version_code,
        update_mode=None if settings.app_update_mode == "none" else settings.app_update_mode,
        store_url=settings.app_update_store_url,
        update_title=settings.app_update_title,
        update_message=settings.app_update_message,
    )
