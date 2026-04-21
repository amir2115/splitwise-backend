from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.domain import ExpenseCreate, ExpenseResponse, ExpenseUpdate
from app.services.crud_service import create_expense, get_expense, list_expenses, serialize_expense, soft_delete_expense, update_expense

router = APIRouter()


@router.get("", response_model=list[ExpenseResponse])
def get_expenses(
    group_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ExpenseResponse]:
    return [serialize_expense(item) for item in list_expenses(db, current_user, group_id=group_id)]


@router.post("", response_model=ExpenseResponse, status_code=201)
def post_expense(payload: ExpenseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ExpenseResponse:
    return serialize_expense(create_expense(db, current_user, payload))


@router.get("/{expense_id}", response_model=ExpenseResponse)
def get_expense_detail(expense_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ExpenseResponse:
    return serialize_expense(get_expense(db, current_user, expense_id))


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def patch_expense(expense_id: str, payload: ExpenseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ExpenseResponse:
    return serialize_expense(update_expense(db, current_user, expense_id, payload))


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> Response:
    soft_delete_expense(db, current_user, expense_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
