from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.notifications import FcmTokenDeleteRequest, FcmTokenResponse, FcmTokenUpsertRequest
from app.services.notification_service import deactivate_fcm_token, register_fcm_token

router = APIRouter()


@router.put("/fcm-token", response_model=FcmTokenResponse)
def upsert_fcm_token(
    payload: FcmTokenUpsertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FcmTokenResponse:
    record = register_fcm_token(db, current_user, payload)
    return FcmTokenResponse(id=record.id, is_active=record.is_active)


@router.delete("/fcm-token", status_code=status.HTTP_204_NO_CONTENT)
def delete_fcm_token(
    payload: FcmTokenDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    deactivate_fcm_token(db, current_user, token=payload.token, device_id=payload.device_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
