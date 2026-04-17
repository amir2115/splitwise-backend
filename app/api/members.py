from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.domain import AddMemberResponse, InlineMemberCreateRequest, MemberCreate, MemberResponse, MemberSuggestionResponse, MemberUpdate
from app.services.crud_service import (
    create_inline_member,
    create_member,
    get_member,
    list_members,
    search_member_suggestions,
    serialize_add_member_result,
    serialize_member,
    serialize_member_suggestion,
    soft_delete_member,
    update_member,
)

router = APIRouter()


@router.get("", response_model=list[MemberResponse])
def get_members(
    group_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MemberResponse]:
    return [serialize_member(item) for item in list_members(db, current_user, group_id=group_id)]


@router.get("/suggestions", response_model=list[MemberSuggestionResponse])
def get_member_suggestions(
    group_id: str,
    query: str = Query(min_length=0, max_length=64),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MemberSuggestionResponse]:
    return [
        serialize_member_suggestion(item)
        for item in search_member_suggestions(db, current_user, group_id=group_id, query=query, limit=limit)
    ]


@router.post("", response_model=AddMemberResponse, status_code=201)
def post_member(payload: MemberCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> AddMemberResponse:
    return serialize_add_member_result(create_member(db, current_user, payload))


@router.post("/inline-create", response_model=AddMemberResponse, status_code=201)
def post_inline_member(
    payload: InlineMemberCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AddMemberResponse:
    return serialize_add_member_result(create_inline_member(db, current_user, payload))


@router.get("/{member_id}", response_model=MemberResponse)
def get_member_detail(member_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MemberResponse:
    return serialize_member(get_member(db, current_user, member_id))


@router.patch("/{member_id}", response_model=MemberResponse)
def patch_member(member_id: str, payload: MemberUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> MemberResponse:
    return serialize_member(update_member(db, current_user, member_id, payload))


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(member_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    soft_delete_member(db, current_user, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
