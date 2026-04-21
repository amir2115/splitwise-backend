from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.domain import GroupCardCreate, GroupCardResponse, GroupCardUpdate
from app.services.crud_service import create_group_card, get_group_card, list_group_cards, serialize_group_card, soft_delete_group_card, update_group_card

router = APIRouter()


@router.get("", response_model=list[GroupCardResponse])
def get_group_cards(
    group_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GroupCardResponse]:
    return [serialize_group_card(item) for item in list_group_cards(db, current_user, group_id=group_id)]


@router.post("", response_model=GroupCardResponse, status_code=201)
def post_group_card(
    payload: GroupCardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupCardResponse:
    return serialize_group_card(create_group_card(db, current_user, payload))


@router.get("/{card_id}", response_model=GroupCardResponse)
def get_group_card_detail(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupCardResponse:
    return serialize_group_card(get_group_card(db, current_user, card_id))


@router.patch("/{card_id}", response_model=GroupCardResponse)
def patch_group_card(
    card_id: str,
    payload: GroupCardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupCardResponse:
    return serialize_group_card(update_group_card(db, current_user, card_id, payload))


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group_card(card_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    soft_delete_group_card(db, current_user, card_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
