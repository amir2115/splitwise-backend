from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Header, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import get_db
from app.schemas.app_download import AppDownloadApkUploadResponse, AppDownloadResponse, AppDownloadUpdate
from app.services.app_download_service import get_app_download_content, update_app_download_content, upload_app_download_apk

router = APIRouter()
settings = get_settings()


def require_app_download_admin(x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret")) -> None:
    if not settings.app_download_admin_secret:
        raise DomainError(
            code="app_download_admin_secret_not_configured",
            message="App download admin secret is not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    if x_admin_secret != settings.app_download_admin_secret:
        raise DomainError(
            code="invalid_app_download_admin_secret",
            message="Invalid app download admin secret",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


@router.get("/app-download", response_model=AppDownloadResponse)
def get_public_app_download(db: Session = Depends(get_db)) -> AppDownloadResponse:
    return get_app_download_content(db)


@router.patch("/admin/app-download", response_model=AppDownloadResponse)
def patch_app_download(
    payload: AppDownloadUpdate,
    _: None = Depends(require_app_download_admin),
    db: Session = Depends(get_db),
) -> AppDownloadResponse:
    return update_app_download_content(db, payload)


@router.post("/admin/app-download/apk", response_model=AppDownloadApkUploadResponse)
async def upload_admin_app_download_apk(
    file: UploadFile = File(...),
    _: None = Depends(require_app_download_admin),
) -> AppDownloadApkUploadResponse:
    content = await file.read()
    return upload_app_download_apk(filename=file.filename, content=content)
