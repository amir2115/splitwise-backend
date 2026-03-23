from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.domain import SettlementCreate, SettlementResponse, SettlementUpdate
from app.services.crud_service import create_settlement, get_settlement, list_settlements, soft_delete_settlement, update_settlement

router = APIRouter()


@router.get("", response_model=list[SettlementResponse])
def get_settlements(
    group_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SettlementResponse]:
    return [SettlementResponse.model_validate(item) for item in list_settlements(db, current_user, group_id=group_id)]


@router.post("", response_model=SettlementResponse, status_code=201)
def post_settlement(
    payload: SettlementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettlementResponse:
    return SettlementResponse.model_validate(create_settlement(db, current_user, payload))


@router.get("/{settlement_id}", response_model=SettlementResponse)
def get_settlement_detail(
    settlement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettlementResponse:
    return SettlementResponse.model_validate(get_settlement(db, current_user, settlement_id))


@router.patch("/{settlement_id}", response_model=SettlementResponse)
def patch_settlement(
    settlement_id: str,
    payload: SettlementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SettlementResponse:
    return SettlementResponse.model_validate(update_settlement(db, current_user, settlement_id, payload))


@router.delete("/{settlement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_settlement(settlement_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    soft_delete_settlement(db, current_user, settlement_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
