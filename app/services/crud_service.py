import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError, NotFoundError
from app.core.time import utcnow
from app.models.domain import Expense, ExpensePayer, ExpenseShare, Group, Member, Settlement, SplitType
from app.models.user import User
from app.schemas.domain import (
    ExpenseCreate,
    ExpenseParticipantAmount,
    ExpenseResponse,
    ExpenseUpdate,
    GroupBalanceResponse,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    MemberBalance,
    MemberCreate,
    MemberResponse,
    MemberUpdate,
    SettlementCreate,
    SettlementResponse,
    SettlementUpdate,
    SimplifiedDebt,
)


def _entity_id(candidate: str | None) -> str:
    return candidate or str(uuid.uuid4())


def _entity_query(model, user: User) -> Select:
    return select(model).where(model.user_id == user.id)


def list_groups(db: Session, user: User) -> list[Group]:
    return list(db.scalars(_entity_query(Group, user).where(Group.deleted_at.is_(None)).order_by(Group.created_at.desc())))


def get_group(db: Session, user: User, group_id: str) -> Group:
    group = db.scalar(_entity_query(Group, user).where(Group.id == group_id))
    if not group:
        raise NotFoundError("Group")
    return group


def create_group(db: Session, user: User, payload: GroupCreate, *, preserve_updated_at: datetime | None = None) -> Group:
    group = Group(id=_entity_id(payload.id), user_id=user.id, name=payload.name)
    if preserve_updated_at:
        group.updated_at = preserve_updated_at
    if payload.deleted_at is not None:
        group.deleted_at = payload.deleted_at
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_group(db: Session, user: User, group_id: str, payload: GroupUpdate) -> Group:
    group = get_group(db, user, group_id)
    if payload.name is not None:
        group.name = payload.name
    if payload.deleted_at is not None:
        group.deleted_at = payload.deleted_at
    group.updated_at = payload.updated_at or payload.deleted_at or utcnow()
    db.commit()
    db.refresh(group)
    return group


def soft_delete_group(db: Session, user: User, group_id: str) -> None:
    group = get_group(db, user, group_id)
    now = utcnow()
    group.deleted_at = now
    group.updated_at = now
    for member in group.members:
        member.deleted_at = now
        member.updated_at = now
    for expense in group.expenses:
        expense.deleted_at = now
        expense.updated_at = now
    for settlement in group.settlements:
        settlement.deleted_at = now
        settlement.updated_at = now
    db.commit()


def list_members(db: Session, user: User, *, group_id: str | None = None) -> list[Member]:
    query = _entity_query(Member, user).where(Member.deleted_at.is_(None))
    if group_id:
        query = query.where(Member.group_id == group_id)
    return list(db.scalars(query.order_by(Member.created_at.asc())))


def get_member(db: Session, user: User, member_id: str) -> Member:
    member = db.scalar(_entity_query(Member, user).where(Member.id == member_id))
    if not member:
        raise NotFoundError("Member")
    return member


def create_member(db: Session, user: User, payload: MemberCreate, *, preserve_updated_at: datetime | None = None) -> Member:
    group = get_group(db, user, payload.group_id)
    if group.deleted_at is not None:
        raise DomainError(code="invalid_group", message="Cannot add members to a deleted group")
    member = Member(
        id=_entity_id(payload.id),
        user_id=user.id,
        group_id=payload.group_id,
        name=payload.name,
        is_archived=payload.is_archived,
    )
    if preserve_updated_at:
        member.updated_at = preserve_updated_at
    if payload.deleted_at is not None:
        member.deleted_at = payload.deleted_at
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def update_member(db: Session, user: User, member_id: str, payload: MemberUpdate) -> Member:
    member = get_member(db, user, member_id)
    if payload.name is not None:
        member.name = payload.name
    if payload.is_archived is not None:
        member.is_archived = payload.is_archived
    if payload.deleted_at is not None:
        member.deleted_at = payload.deleted_at
    member.updated_at = payload.updated_at or payload.deleted_at or utcnow()
    db.commit()
    db.refresh(member)
    return member


def soft_delete_member(db: Session, user: User, member_id: str) -> None:
    member = get_member(db, user, member_id)
    member.deleted_at = utcnow()
    member.updated_at = member.deleted_at
    db.commit()


def _validate_members_in_group(db: Session, user: User, group_id: str, member_ids: list[str]) -> dict[str, Member]:
    members = list(
        db.scalars(
            select(Member).where(
                Member.user_id == user.id,
                Member.group_id == group_id,
                Member.id.in_(member_ids),
                Member.deleted_at.is_(None),
            )
        )
    )
    member_map = {member.id: member for member in members}
    missing = sorted(set(member_ids) - set(member_map))
    if missing:
        raise DomainError(code="invalid_member", message=f"Members not found in group: {', '.join(missing)}")
    return member_map


def _normalize_equal_shares(total_amount: int, members: list[str]) -> list[ExpenseParticipantAmount]:
    sorted_ids = sorted(members)
    base_amount = total_amount // len(sorted_ids)
    remainder = total_amount % len(sorted_ids)
    results: list[ExpenseParticipantAmount] = []
    for index, member_id in enumerate(sorted_ids):
        amount = base_amount + (1 if index < remainder else 0)
        results.append(ExpenseParticipantAmount(member_id=member_id, amount=amount))
    return results


def _validate_expense_payload(db: Session, user: User, payload: ExpenseCreate | ExpenseUpdate, *, group_id: str) -> tuple[list[ExpenseParticipantAmount], list[ExpenseParticipantAmount]]:
    total_amount = payload.total_amount
    split_type = payload.split_type
    payers = payload.payers or []
    shares = payload.shares or []

    if total_amount is None or total_amount <= 0:
        raise DomainError(code="invalid_expense", message="Total amount must be positive")
    if not payers:
        raise DomainError(code="invalid_expense", message="At least one payer is required")
    if not shares:
        raise DomainError(code="invalid_expense", message="At least one share is required")
    if any(item.amount < 0 for item in payers) or any(item.amount < 0 for item in shares):
        raise DomainError(code="invalid_expense", message="Negative payer or share amounts are invalid")
    if sum(item.amount for item in payers) != total_amount:
        raise DomainError(code="invalid_expense", message="Payer amounts must sum to total amount")

    all_member_ids = [item.member_id for item in payers] + [item.member_id for item in shares]
    _validate_members_in_group(db, user, group_id, all_member_ids)

    if split_type == SplitType.EQUAL:
        normalized_shares = _normalize_equal_shares(total_amount, [item.member_id for item in shares])
        return payers, normalized_shares

    if sum(item.amount for item in shares) != total_amount:
        raise DomainError(code="invalid_expense", message="Share amounts must sum to total amount for EXACT splits")
    return payers, shares


def _apply_expense_children(expense: Expense, payers: list[ExpenseParticipantAmount], shares: list[ExpenseParticipantAmount]) -> None:
    expense.payers.clear()
    expense.shares.clear()
    expense.payers.extend(
        ExpensePayer(expense_id=expense.id, member_id=item.member_id, amount_paid=item.amount) for item in payers
    )
    expense.shares.extend(
        ExpenseShare(expense_id=expense.id, member_id=item.member_id, amount_owed=item.amount) for item in shares
    )


def _expense_query(user: User) -> Select:
    return (
        select(Expense)
        .where(Expense.user_id == user.id)
        .options(selectinload(Expense.payers), selectinload(Expense.shares))
    )


def list_expenses(db: Session, user: User, *, group_id: str | None = None) -> list[Expense]:
    query = _expense_query(user).where(Expense.deleted_at.is_(None))
    if group_id:
        query = query.where(Expense.group_id == group_id)
    return list(db.scalars(query.order_by(Expense.created_at.desc())).unique())


def get_expense(db: Session, user: User, expense_id: str) -> Expense:
    expense = db.scalar(_expense_query(user).where(Expense.id == expense_id))
    if not expense:
        raise NotFoundError("Expense")
    return expense


def create_expense(db: Session, user: User, payload: ExpenseCreate) -> Expense:
    group = get_group(db, user, payload.group_id)
    if group.deleted_at is not None:
        raise DomainError(code="invalid_group", message="Cannot add expenses to a deleted group")
    payers, shares = _validate_expense_payload(db, user, payload, group_id=payload.group_id)
    expense = Expense(
        id=_entity_id(payload.id),
        user_id=user.id,
        group_id=payload.group_id,
        title=payload.title,
        note=payload.note,
        total_amount=payload.total_amount,
        split_type=payload.split_type,
    )
    if payload.updated_at:
        expense.updated_at = payload.updated_at
    _apply_expense_children(expense, payers, shares)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return get_expense(db, user, expense.id)


def update_expense(db: Session, user: User, expense_id: str, payload: ExpenseUpdate) -> Expense:
    expense = get_expense(db, user, expense_id)
    merged = ExpenseCreate(
        id=expense.id,
        group_id=expense.group_id,
        title=payload.title if payload.title is not None else expense.title,
        note=payload.note if payload.note is not None else expense.note,
        total_amount=payload.total_amount if payload.total_amount is not None else expense.total_amount,
        split_type=payload.split_type if payload.split_type is not None else expense.split_type,
        payers=payload.payers if payload.payers is not None else [ExpenseParticipantAmount(member_id=item.member_id, amount=item.amount_paid) for item in expense.payers],
        shares=payload.shares if payload.shares is not None else [ExpenseParticipantAmount(member_id=item.member_id, amount=item.amount_owed) for item in expense.shares],
        updated_at=payload.updated_at or utcnow(),
    )
    payers, shares = _validate_expense_payload(db, user, merged, group_id=expense.group_id)
    expense.title = merged.title
    expense.note = merged.note
    expense.total_amount = merged.total_amount
    expense.split_type = merged.split_type
    if payload.deleted_at is not None:
        expense.deleted_at = payload.deleted_at
    expense.updated_at = merged.updated_at
    _apply_expense_children(expense, payers, shares)
    db.commit()
    return get_expense(db, user, expense.id)


def soft_delete_expense(db: Session, user: User, expense_id: str) -> None:
    expense = get_expense(db, user, expense_id)
    expense.deleted_at = utcnow()
    expense.updated_at = expense.deleted_at
    db.commit()


def list_settlements(db: Session, user: User, *, group_id: str | None = None) -> list[Settlement]:
    query = select(Settlement).where(Settlement.user_id == user.id, Settlement.deleted_at.is_(None))
    if group_id:
        query = query.where(Settlement.group_id == group_id)
    return list(db.scalars(query.order_by(Settlement.created_at.desc())))


def get_settlement(db: Session, user: User, settlement_id: str) -> Settlement:
    settlement = db.scalar(select(Settlement).where(Settlement.user_id == user.id, Settlement.id == settlement_id))
    if not settlement:
        raise NotFoundError("Settlement")
    return settlement


def _validate_settlement(db: Session, user: User, group_id: str, from_member_id: str, to_member_id: str, amount: int) -> None:
    if amount <= 0:
        raise DomainError(code="invalid_settlement", message="Settlement amount must be positive")
    if from_member_id == to_member_id:
        raise DomainError(code="invalid_settlement", message="Settlement members must be different")
    _validate_members_in_group(db, user, group_id, [from_member_id, to_member_id])


def create_settlement(db: Session, user: User, payload: SettlementCreate) -> Settlement:
    group = get_group(db, user, payload.group_id)
    if group.deleted_at is not None:
        raise DomainError(code="invalid_group", message="Cannot add settlements to a deleted group")
    _validate_settlement(db, user, payload.group_id, payload.from_member_id, payload.to_member_id, payload.amount)
    settlement = Settlement(
        id=_entity_id(payload.id),
        user_id=user.id,
        group_id=payload.group_id,
        from_member_id=payload.from_member_id,
        to_member_id=payload.to_member_id,
        amount=payload.amount,
        note=payload.note,
    )
    if payload.updated_at:
        settlement.updated_at = payload.updated_at
    if getattr(payload, "deleted_at", None) is not None:
        settlement.deleted_at = payload.deleted_at
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return settlement


def update_settlement(db: Session, user: User, settlement_id: str, payload: SettlementUpdate) -> Settlement:
    settlement = get_settlement(db, user, settlement_id)
    from_member_id = payload.from_member_id or settlement.from_member_id
    to_member_id = payload.to_member_id or settlement.to_member_id
    amount = payload.amount or settlement.amount
    _validate_settlement(db, user, settlement.group_id, from_member_id, to_member_id, amount)
    settlement.from_member_id = from_member_id
    settlement.to_member_id = to_member_id
    settlement.amount = amount
    if payload.note is not None:
        settlement.note = payload.note
    if payload.deleted_at is not None:
        settlement.deleted_at = payload.deleted_at
    settlement.updated_at = payload.updated_at or payload.deleted_at or utcnow()
    db.commit()
    db.refresh(settlement)
    return settlement


def soft_delete_settlement(db: Session, user: User, settlement_id: str) -> None:
    settlement = get_settlement(db, user, settlement_id)
    settlement.deleted_at = utcnow()
    settlement.updated_at = settlement.deleted_at
    db.commit()


def serialize_expense(expense: Expense) -> ExpenseResponse:
    return ExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        title=expense.title,
        note=expense.note,
        total_amount=expense.total_amount,
        split_type=expense.split_type,
        created_at=expense.created_at,
        updated_at=expense.updated_at,
        deleted_at=expense.deleted_at,
        user_id=expense.user_id,
        payers=[ExpenseParticipantAmount(member_id=item.member_id, amount=item.amount_paid) for item in expense.payers],
        shares=[ExpenseParticipantAmount(member_id=item.member_id, amount=item.amount_owed) for item in expense.shares],
    )


def calculate_group_balances(db: Session, user: User, group_id: str) -> GroupBalanceResponse:
    group = db.scalar(
        select(Group)
        .where(Group.user_id == user.id, Group.id == group_id)
        .options(
            selectinload(Group.members),
            selectinload(Group.expenses).selectinload(Expense.payers),
            selectinload(Group.expenses).selectinload(Expense.shares),
            selectinload(Group.settlements),
        )
    )
    if not group:
        raise NotFoundError("Group")

    active_members = sorted(
        (member for member in group.members if member.deleted_at is None),
        key=lambda item: (item.created_at, item.id),
    )
    paid_totals = defaultdict(int)
    owed_totals = defaultdict(int)

    for expense in group.expenses:
        if expense.deleted_at is not None:
            continue
        for payer in expense.payers:
            paid_totals[payer.member_id] += payer.amount_paid
        for share in expense.shares:
            owed_totals[share.member_id] += share.amount_owed

    for settlement in group.settlements:
        if settlement.deleted_at is not None:
            continue
        paid_totals[settlement.from_member_id] += settlement.amount
        owed_totals[settlement.to_member_id] += settlement.amount

    balances: list[MemberBalance] = []
    creditors: list[list[str | int]] = []
    debtors: list[list[str | int]] = []
    for member in active_members:
        paid_total = paid_totals[member.id]
        owed_total = owed_totals[member.id]
        net_balance = paid_total - owed_total
        balances.append(
            MemberBalance(
                member_id=member.id,
                member_name=member.name,
                paid_total=paid_total,
                owed_total=owed_total,
                net_balance=net_balance,
            )
        )
        if net_balance > 0:
            creditors.append([member.id, net_balance])
        elif net_balance < 0:
            debtors.append([member.id, -net_balance])

    creditors.sort(key=lambda item: (-int(item[1]), str(item[0])))
    debtors.sort(key=lambda item: (int(item[1]), str(item[0])))

    simplified_debts: list[SimplifiedDebt] = []
    creditor_index = 0
    debtor_index = 0
    while creditor_index < len(creditors) and debtor_index < len(debtors):
        creditor_id, credit_remaining = creditors[creditor_index]
        debtor_id, debt_remaining = debtors[debtor_index]
        amount = min(credit_remaining, debt_remaining)
        simplified_debts.append(SimplifiedDebt(from_member_id=str(debtor_id), to_member_id=str(creditor_id), amount=int(amount)))
        creditors[creditor_index][1] = int(credit_remaining) - int(amount)
        debtors[debtor_index][1] = int(debt_remaining) - int(amount)
        if creditors[creditor_index][1] == 0:
            creditor_index += 1
        if debtors[debtor_index][1] == 0:
            debtor_index += 1

    return GroupBalanceResponse(group_id=group.id, balances=balances, simplified_debts=simplified_debts)
