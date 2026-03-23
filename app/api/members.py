from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.domain import MemberCreate, MemberResponse, MemberUpdate
from app.services.crud_service import create_member, get_member, list_members, soft_delete_member, update_member

router = APIRouter()


@router.get("", response_model=list[MemberResponse])
def get_members(
    group_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MemberResponse]:
    return [MemberResponse.model_validate(item) for item in list_members(db, current_user, group_id=group_id)]


@router.post("", response_model=MemberResponse, status_code=201)
def post_member(payload: MemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MemberResponse:
    return MemberResponse.model_validate(create_member(db, current_user, payload))


@router.get("/{member_id}", response_model=MemberResponse)
def get_member_detail(member_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MemberResponse:
    return MemberResponse.model_validate(get_member(db, current_user, member_id))


@router.patch("/{member_id}", response_model=MemberResponse)
def patch_member(member_id: str, payload: MemberUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MemberResponse:
    return MemberResponse.model_validate(update_member(db, current_user, member_id, payload))


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    soft_delete_member(db, current_user, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
