from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.admin import PublicSiteSettingsResponse
from app.services.runtime_settings_service import list_public_site_settings

router = APIRouter()


@router.get("/site-settings", response_model=PublicSiteSettingsResponse)
def get_public_site_settings(db: Session = Depends(get_db)) -> PublicSiteSettingsResponse:
    return PublicSiteSettingsResponse(**list_public_site_settings(db))
