import logging
from typing import Optional

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import resolve_store_url
from app.api.router import api_router
from app.core.config import DEFAULT_CORS_ALLOW_ORIGINS, get_settings
from app.core.errors import DomainError
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=DEFAULT_CORS_ALLOW_ORIGINS,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)
logger.info("CORS allow origins: %s", DEFAULT_CORS_ALLOW_ORIGINS)


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
                "details": exc.errors(),
            }
        },
    )


app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", response_model=HealthResponse)
def root_health(x_app_store: Optional[str] = Header(default=None)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        min_supported_version_code=settings.app_min_supported_version_code,
        latest_version_code=settings.app_latest_version_code,
        update_mode=None if settings.app_update_mode == "none" else settings.app_update_mode,
        store_url=resolve_store_url(x_app_store),
        update_title=settings.app_update_title,
        update_message=settings.app_update_message,
    )
