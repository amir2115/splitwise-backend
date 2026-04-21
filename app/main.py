import logging
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import DomainError, NotFoundError
from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services.app_download_service import APP_DOWNLOAD_APK_FILENAME
from app.services.health_service import build_health_response

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
logger.info("CORS allow origins: %s", settings.cors_allow_origins)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.detail)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": jsonable_encoder(exc.errors(), custom_encoder={ValueError: str}),
            }
        },
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/files/{filename}")
def download_uploaded_file(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    if safe_name != filename or safe_name != APP_DOWNLOAD_APK_FILENAME:
        raise NotFoundError("file")

    file_path = Path(settings.app_download_upload_dir) / safe_name
    if not file_path.is_file():
        raise NotFoundError("file")

    return FileResponse(path=file_path, filename=safe_name, media_type="application/vnd.android.package-archive")


@app.get("/health", response_model=HealthResponse)
def root_health(
    x_app_store: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> HealthResponse:
    return build_health_response(db, x_app_store)
