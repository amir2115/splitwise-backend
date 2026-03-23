from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.domain import GroupBalanceResponse, GroupCreate, GroupResponse, GroupUpdate
from app.services.crud_service import calculate_group_balances, create_group, get_group, list_groups, soft_delete_group, update_group

router = APIRouter()


@router.get("", response_model=list[GroupResponse])
def get_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[GroupResponse]:
    return [GroupResponse.model_validate(item) for item in list_groups(db, current_user)]


@router.post("", response_model=GroupResponse, status_code=201)
def post_group(payload: GroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> GroupResponse:
    return GroupResponse.model_validate(create_group(db, current_user, payload))


@router.get("/{group_id}", response_model=GroupResponse)
def get_group_detail(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> GroupResponse:
    return GroupResponse.model_validate(get_group(db, current_user, group_id))


@router.patch("/{group_id}", response_model=GroupResponse)
def patch_group(group_id: str, payload: GroupUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> GroupResponse:
    return GroupResponse.model_validate(update_group(db, current_user, group_id, payload))


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    soft_delete_group(db, current_user, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{group_id}/balances", response_model=GroupBalanceResponse)
def group_balances(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> GroupBalanceResponse:
    return calculate_group_balances(db, current_user, group_id)
