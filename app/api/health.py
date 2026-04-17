from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.services.health_service import build_health_response

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(
    x_app_store: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> HealthResponse:
    return build_health_response(db, x_app_store)
