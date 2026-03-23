from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError
from app.core.time import ensure_utc, utcnow
from app.models.domain import Expense, Group, Member, Settlement
from app.models.user import User
from app.schemas.domain import ExpenseUpdate, GroupUpdate, MemberUpdate, SettlementUpdate
from app.schemas.sync import InitialImportRequest, SyncPullResponse, SyncRequest, SyncResponse
from app.services.crud_service import (
    create_expense,
    create_group,
    create_member,
    create_settlement,
    get_expense,
    get_group,
    get_member,
    get_settlement,
    serialize_expense,
    update_expense,
    update_group,
    update_member,
    update_settlement,
)


def _is_newer(client_updated_at: datetime | None, server_updated_at: datetime) -> bool:
    return client_updated_at is not None and ensure_utc(client_updated_at) > ensure_utc(server_updated_at)


def _upsert_group(db: Session, user: User, payload) -> None:
    existing = db.get(Group, payload.id) if payload.id else None
    if not existing:
        create_group(db, user, payload, preserve_updated_at=getattr(payload, "updated_at", None))
        return
    if existing.user_id != user.id:
        raise DomainError(code="sync_conflict", message="Cannot import a group owned by another user")
    if _is_newer(getattr(payload, "updated_at", None), existing.updated_at):
        update_group(
            db,
            user,
            existing.id,
            GroupUpdate(
                name=payload.name,
                deleted_at=getattr(payload, "deleted_at", None),
                updated_at=getattr(payload, "updated_at", None),
            ),
        )


def _upsert_member(db: Session, user: User, payload) -> None:
    existing = db.get(Member, payload.id) if payload.id else None
    if not existing:
        create_member(db, user, payload, preserve_updated_at=getattr(payload, "updated_at", None))
        return
    if existing.user_id != user.id:
        raise DomainError(code="sync_conflict", message="Cannot import a member owned by another user")
    if _is_newer(getattr(payload, "updated_at", None), existing.updated_at):
        update_member(
            db,
            user,
            existing.id,
            MemberUpdate(
                name=payload.name,
                is_archived=payload.is_archived,
                deleted_at=getattr(payload, "deleted_at", None),
                updated_at=getattr(payload, "updated_at", None),
            ),
        )


def _upsert_expense(db: Session, user: User, payload) -> None:
    existing = db.get(Expense, payload.id) if payload.id else None
    if not existing:
        create_expense(db, user, payload)
        return
    if existing.user_id != user.id:
        raise DomainError(code="sync_conflict", message="Cannot import an expense owned by another user")
    if _is_newer(getattr(payload, "updated_at", None), existing.updated_at):
        update_expense(
            db,
            user,
            existing.id,
            ExpenseUpdate(
                title=payload.title,
                note=payload.note,
                total_amount=payload.total_amount,
                split_type=payload.split_type,
                payers=payload.payers,
                shares=payload.shares,
                deleted_at=getattr(payload, "deleted_at", None),
                updated_at=getattr(payload, "updated_at", None),
            ),
        )


def _upsert_settlement(db: Session, user: User, payload) -> None:
    existing = db.get(Settlement, payload.id) if payload.id else None
    if not existing:
        create_settlement(db, user, payload)
        return
    if existing.user_id != user.id:
        raise DomainError(code="sync_conflict", message="Cannot import a settlement owned by another user")
    if _is_newer(getattr(payload, "updated_at", None), existing.updated_at):
        update_settlement(
            db,
            user,
            existing.id,
            SettlementUpdate(
                from_member_id=payload.from_member_id,
                to_member_id=payload.to_member_id,
                amount=payload.amount,
                note=payload.note,
                deleted_at=getattr(payload, "deleted_at", None),
                updated_at=getattr(payload, "updated_at", None),
            ),
        )


def _apply_tombstone(db: Session, model, user: User, entity_id: str, deleted_at: datetime) -> None:
    entity = db.get(model, entity_id)
    if entity and entity.user_id == user.id and deleted_at > entity.updated_at:
        entity.deleted_at = deleted_at
        entity.updated_at = deleted_at
        db.commit()


def _serialize_group(group: Group) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "created_at": group.created_at,
        "updated_at": group.updated_at,
        "deleted_at": group.deleted_at,
        "user_id": group.user_id,
    }


def _serialize_member(member: Member) -> dict:
    return {
        "id": member.id,
        "group_id": member.group_id,
        "name": member.name,
        "is_archived": member.is_archived,
        "created_at": member.created_at,
        "updated_at": member.updated_at,
        "deleted_at": member.deleted_at,
        "user_id": member.user_id,
    }


def _serialize_settlement(settlement: Settlement) -> dict:
    return {
        "id": settlement.id,
        "group_id": settlement.group_id,
        "from_member_id": settlement.from_member_id,
        "to_member_id": settlement.to_member_id,
        "amount": settlement.amount,
        "note": settlement.note,
        "created_at": settlement.created_at,
        "updated_at": settlement.updated_at,
        "deleted_at": settlement.deleted_at,
        "user_id": settlement.user_id,
    }


def initial_import(db: Session, user: User, payload: InitialImportRequest) -> SyncResponse:
    if db.scalar(select(Group.id).where(Group.user_id == user.id).limit(1)):
        raise DomainError(code="import_not_allowed", message="Initial import can only run before any synced data exists")
    return sync_user_data(db, user, SyncRequest(device_id=payload.device_id, last_synced_at=None, push=payload))


def sync_user_data(db: Session, user: User, request: SyncRequest) -> SyncResponse:
    if request.push:
        for group in request.push.groups:
            _upsert_group(db, user, group)
        for member in request.push.members:
            _upsert_member(db, user, member)
        for expense in request.push.expenses:
            _upsert_expense(db, user, expense)
        for settlement in request.push.settlements:
            _upsert_settlement(db, user, settlement)

        now = utcnow()
        for entity_id in request.push.deleted_group_ids:
            _apply_tombstone(db, Group, user, entity_id, now)
        for entity_id in request.push.deleted_member_ids:
            _apply_tombstone(db, Member, user, entity_id, now)
        for entity_id in request.push.deleted_expense_ids:
            _apply_tombstone(db, Expense, user, entity_id, now)
        for entity_id in request.push.deleted_settlement_ids:
            _apply_tombstone(db, Settlement, user, entity_id, now)

    cursor = request.last_synced_at
    server_time = utcnow()

    group_query = select(Group).where(Group.user_id == user.id)
    member_query = select(Member).where(Member.user_id == user.id)
    expense_query = (
        select(Expense)
        .where(Expense.user_id == user.id)
        .options(selectinload(Expense.payers), selectinload(Expense.shares))
    )
    settlement_query = select(Settlement).where(Settlement.user_id == user.id)
    if cursor:
        group_query = group_query.where(Group.updated_at > cursor)
        member_query = member_query.where(Member.updated_at > cursor)
        expense_query = expense_query.where(Expense.updated_at > cursor)
        settlement_query = settlement_query.where(Settlement.updated_at > cursor)

    groups = list(db.scalars(group_query))
    members = list(db.scalars(member_query))
    expenses = list(db.scalars(expense_query).unique())
    settlements = list(db.scalars(settlement_query))

    changes = SyncPullResponse(
        groups=[_serialize_group(group) for group in groups if group.deleted_at is None],
        members=[_serialize_member(member) for member in members if member.deleted_at is None],
        expenses=[serialize_expense(expense).model_dump(mode="json") for expense in expenses if expense.deleted_at is None],
        settlements=[_serialize_settlement(item) for item in settlements if item.deleted_at is None],
        deleted_group_ids=[group.id for group in groups if group.deleted_at is not None],
        deleted_member_ids=[member.id for member in members if member.deleted_at is not None],
        deleted_expense_ids=[expense.id for expense in expenses if expense.deleted_at is not None],
        deleted_settlement_ids=[item.id for item in settlements if item.deleted_at is not None],
    )
    return SyncResponse(server_time=server_time, next_cursor=server_time, changes=changes)
