from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.domain import GroupInviteStatus
from app.models.user import User
from app.schemas.domain import GroupInviteResponse
from app.services.crud_service import (
    accept_group_invite,
    list_group_invites,
    reject_group_invite,
    serialize_group_invite,
)

router = APIRouter()


def _parse_status(status: Optional[str]) -> Optional[GroupInviteStatus]:
    if status is None:
        return GroupInviteStatus.PENDING
    normalized = status.strip().upper()
    if normalized == "":
        return None
    try:
        return GroupInviteStatus(normalized)
    except ValueError as exc:
        raise DomainError(
            code="validation_error",
            message="Request validation failed",
            details=[
                {
                    "type": "enum",
                    "loc": ["query", "status"],
                    "msg": "Input should be 'PENDING', 'ACCEPTED' or 'REJECTED'",
                    "input": status,
                    "ctx": {"expected": "'PENDING', 'ACCEPTED' or 'REJECTED'"},
                }
            ],
            status_code=422,
        ) from exc


@router.get("", response_model=list[GroupInviteResponse])
def get_invites(
    status: Optional[str] = Query(default="pending"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GroupInviteResponse]:
    return [serialize_group_invite(item) for item in list_group_invites(db, current_user, status=_parse_status(status))]


@router.post("/{invite_id}/accept", response_model=GroupInviteResponse)
def post_accept_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupInviteResponse:
    return serialize_group_invite(accept_group_invite(db, current_user, invite_id))


@router.post("/{invite_id}/reject", response_model=GroupInviteResponse)
def post_reject_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupInviteResponse:
    return serialize_group_invite(reject_group_invite(db, current_user, invite_id))
