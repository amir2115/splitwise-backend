import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import DomainError, NotFoundError
from app.core.time import utcnow
from app.models.domain import (
    Expense,
    ExpensePayer,
    ExpenseShare,
    Group,
    GroupCard,
    GroupInvite,
    GroupInviteStatus,
    GroupMembership,
    Member,
    MembershipStatus,
    Settlement,
    SplitType,
    UserConnection,
)
from app.models.user import User
from app.schemas.auth import UserCreateByInviter
from app.services.auth_service import create_user_by_inviter
from app.schemas.domain import (
    AddMemberResponse,
    ExpenseCreate,
    ExpenseParticipantAmount,
    ExpenseResponse,
    ExpenseUpdate,
    GroupBalanceResponse,
    GroupCardCreate,
    GroupCardResponse,
    GroupCardUpdate,
    GroupCreate,
    GroupInviteResponse,
    GroupResponse,
    GroupUpdate,
    InlineMemberCreateRequest,
    MemberBalance,
    MemberCreate,
    MemberSuggestionResponse,
    MemberResponse,
    MemberUpdate,
    SettlementCreate,
    SettlementResponse,
    SettlementUpdate,
    SimplifiedDebt,
)


@dataclass
class AddMemberResult:
    outcome: str
    member: Member


def _entity_id(candidate: str | None) -> str:
    return candidate or str(uuid.uuid4())


def _normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3:
        raise DomainError(code="invalid_username", message="Username must be at least 3 characters long")
    if len(normalized) > 64:
        raise DomainError(code="invalid_username", message="Username must be at most 64 characters long")
    return normalized


def _normalize_digits(input_value: str) -> str:
    return input_value.replace("٠", "0").replace("١", "1").replace("٢", "2").replace("٣", "3").replace("٤", "4").replace(
        "٥", "5"
    ).replace("٦", "6").replace("٧", "7").replace("٨", "8").replace("٩", "9").replace("۰", "0").replace("۱", "1").replace(
        "۲", "2"
    ).replace("۳", "3").replace("۴", "4").replace("۵", "5").replace("۶", "6").replace("۷", "7").replace("۸", "8").replace(
        "۹", "9"
    )


def _normalize_card_number(card_number: str) -> str:
    normalized = "".join(char for char in _normalize_digits(card_number) if char.isdigit())
    if len(normalized) != 16:
        raise DomainError(code="invalid_group_card", message="Card number must be exactly 16 digits")
    if not normalized.isascii():
        raise DomainError(code="invalid_group_card", message="Card number must contain ASCII digits only")
    return normalized


def _connection_pair(left_user_id: str, right_user_id: str) -> tuple[str, str]:
    return tuple(sorted((left_user_id, right_user_id)))


def _active_group_ids_query(user: User):
    return select(GroupMembership.group_id).where(
        GroupMembership.user_id == user.id,
        GroupMembership.status == MembershipStatus.ACTIVE,
    )


def _active_group_query(user: User) -> Select:
    return (
        select(Group)
        .join(
            GroupMembership,
            and_(
                GroupMembership.group_id == Group.id,
                GroupMembership.user_id == user.id,
                GroupMembership.status == MembershipStatus.ACTIVE,
            ),
        )
        .distinct()
    )


def _find_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == _normalize_username(username)))


def _is_connected(db: Session, left_user_id: str, right_user_id: str) -> bool:
    if left_user_id == right_user_id:
        return True
    low_id, high_id = _connection_pair(left_user_id, right_user_id)
    return db.scalar(
        select(UserConnection.id).where(
            UserConnection.user_low_id == low_id,
            UserConnection.user_high_id == high_id,
        )
    ) is not None


def _ensure_connection(db: Session, left_user_id: str, right_user_id: str) -> None:
    if left_user_id == right_user_id:
        return
    low_id, high_id = _connection_pair(left_user_id, right_user_id)
    existing = db.scalar(
        select(UserConnection).where(
            UserConnection.user_low_id == low_id,
            UserConnection.user_high_id == high_id,
        )
    )
    if not existing:
        db.add(UserConnection(user_low_id=low_id, user_high_id=high_id))


def _ensure_group_membership(db: Session, group_id: str, user_id: str, status: MembershipStatus) -> GroupMembership:
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if membership:
        membership.status = status
        membership.updated_at = utcnow()
        return membership
    membership = GroupMembership(group_id=group_id, user_id=user_id, status=status)
    db.add(membership)
    return membership


def _ensure_active_member_rows(db: Session, group: Group) -> None:
    memberships = list(
        db.scalars(
            select(GroupMembership).where(
                GroupMembership.group_id == group.id,
                GroupMembership.status == MembershipStatus.ACTIVE,
            )
        )
    )
    if not memberships:
        return

    active_members = list(
        db.scalars(
            select(Member).where(
                Member.group_id == group.id,
                Member.deleted_at.is_(None),
                Member.linked_user_id.is_not(None),
            )
        )
    )
    members_by_user_id = {member.linked_user_id: member for member in active_members if member.linked_user_id is not None}
    created = False
    for membership in memberships:
        user = db.get(User, membership.user_id)
        if not user:
            continue
        existing = members_by_user_id.get(user.id)
        if existing:
            if existing.membership_status != MembershipStatus.ACTIVE or existing.username != user.username:
                existing.membership_status = MembershipStatus.ACTIVE
                existing.username = user.username
                existing.linked_user_id = user.id
                existing.updated_at = utcnow()
                created = True
            continue
        db.add(
            Member(
                user_id=group.user_id,
                group_id=group.id,
                username=user.username,
                linked_user_id=user.id,
                membership_status=MembershipStatus.ACTIVE,
                is_archived=False,
            )
        )
        created = True
    if created:
        group.updated_at = utcnow()
        db.commit()
        db.refresh(group)


def _delete_group_membership(db: Session, group_id: str, user_id: str) -> None:
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == group_id,
            GroupMembership.user_id == user_id,
        )
    )
    if membership:
        db.delete(membership)


def _serialize_group(group: Group) -> GroupResponse:
    return GroupResponse.model_validate(group)


def serialize_member(member: Member) -> MemberResponse:
    return MemberResponse(
        id=member.id,
        group_id=member.group_id,
        username=member.username,
        membership_status=member.membership_status,
        is_archived=member.is_archived,
        user_id=member.linked_user_id,
        created_at=member.created_at,
        updated_at=member.updated_at,
        deleted_at=member.deleted_at,
    )


def serialize_group_card(group_card: GroupCard) -> GroupCardResponse:
    return GroupCardResponse(
        id=group_card.id,
        group_id=group_card.group_id,
        member_id=group_card.member_id,
        card_number=group_card.card_number,
        user_id=group_card.user_id,
        created_at=group_card.created_at,
        updated_at=group_card.updated_at,
        deleted_at=group_card.deleted_at,
    )


def serialize_add_member_result(result: AddMemberResult) -> AddMemberResponse:
    return AddMemberResponse(outcome=result.outcome, member=serialize_member(result.member))


def serialize_member_suggestion(user: User) -> MemberSuggestionResponse:
    return MemberSuggestionResponse(id=user.id, username=user.username, name=user.name)


def serialize_group_invite(invite: GroupInvite) -> GroupInviteResponse:
    return GroupInviteResponse(
        id=invite.id,
        group_id=invite.group_id,
        group_name=invite.group.name,
        member_id=invite.member_id,
        username=invite.member.username,
        inviter_user_id=invite.inviter_user_id,
        inviter_username=invite.inviter_user.username,
        invitee_user_id=invite.invitee_user_id,
        invitee_username=invite.invitee_user.username,
        status=invite.status,
        responded_at=invite.responded_at,
        created_at=invite.created_at,
        updated_at=invite.updated_at,
        deleted_at=None,
    )


def list_groups(db: Session, user: User) -> list[Group]:
    groups = list(db.scalars(_active_group_query(user).where(Group.deleted_at.is_(None)).order_by(Group.created_at.desc())))
    for group in groups:
        _ensure_active_member_rows(db, group)
    return groups


def get_group(db: Session, user: User, group_id: str) -> Group:
    group = db.scalar(_active_group_query(user).where(Group.id == group_id))
    if not group:
        raise NotFoundError("Group")
    _ensure_active_member_rows(db, group)
    return group


def create_group(db: Session, user: User, payload: GroupCreate, *, preserve_updated_at: datetime | None = None) -> Group:
    group = Group(id=_entity_id(payload.id), user_id=user.id, name=payload.name)
    if preserve_updated_at:
        group.updated_at = preserve_updated_at
    if payload.deleted_at is not None:
        group.deleted_at = payload.deleted_at
    db.add(group)
    db.flush()
    _ensure_group_membership(db, group.id, user.id, MembershipStatus.ACTIVE)
    db.add(
        Member(
            user_id=user.id,
            group_id=group.id,
            username=user.username,
            linked_user_id=user.id,
            membership_status=MembershipStatus.ACTIVE,
            is_archived=False,
        )
    )
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
    for group_card in group.group_cards:
        group_card.deleted_at = now
        group_card.updated_at = now
    db.commit()


def _get_active_group_member(db: Session, group_id: str, member_id: str) -> Member:
    member = db.scalar(
        select(Member).where(
            Member.id == member_id,
            Member.group_id == group_id,
            Member.deleted_at.is_(None),
            Member.membership_status == MembershipStatus.ACTIVE,
        )
    )
    if not member:
        raise DomainError(code="invalid_group_card_member", message="Card member must be an active member of the group")
    return member


def _find_group_card_by_number(db: Session, group_id: str, card_number: str) -> GroupCard | None:
    return db.scalar(
        select(GroupCard).where(
            GroupCard.group_id == group_id,
            GroupCard.card_number == card_number,
            GroupCard.deleted_at.is_(None),
        )
    )


def list_group_cards(db: Session, user: User, *, group_id: str | None = None) -> list[GroupCard]:
    query = (
        select(GroupCard)
        .where(
            GroupCard.group_id.in_(_active_group_ids_query(user)),
            GroupCard.deleted_at.is_(None),
        )
        .options(selectinload(GroupCard.member))
    )
    if group_id:
        get_group(db, user, group_id)
        query = query.where(GroupCard.group_id == group_id)
    return list(db.scalars(query.order_by(GroupCard.created_at.desc())).unique())


def get_group_card(db: Session, user: User, card_id: str) -> GroupCard:
    group_card = db.scalar(
        select(GroupCard)
        .where(
            GroupCard.id == card_id,
            GroupCard.group_id.in_(_active_group_ids_query(user)),
        )
        .options(selectinload(GroupCard.member))
    )
    if not group_card:
        raise NotFoundError("Group card")
    return group_card


def create_group_card(db: Session, user: User, payload: GroupCardCreate) -> GroupCard:
    group = get_group(db, user, payload.group_id)
    if group.deleted_at is not None:
        raise DomainError(code="invalid_group", message="Cannot add cards to a deleted group")
    member = _get_active_group_member(db, payload.group_id, payload.member_id)
    normalized_card_number = _normalize_card_number(payload.card_number)
    existing = _find_group_card_by_number(db, payload.group_id, normalized_card_number)
    if existing:
        raise DomainError(code="duplicate_group_card", message="Card number already exists in this group")

    group_card = GroupCard(
        id=_entity_id(payload.id),
        user_id=user.id,
        group_id=payload.group_id,
        member_id=member.id,
        card_number=normalized_card_number,
    )
    if payload.updated_at:
        group_card.updated_at = payload.updated_at
    if payload.deleted_at is not None:
        group_card.deleted_at = payload.deleted_at
    db.add(group_card)
    db.commit()
    db.refresh(group_card)
    return get_group_card(db, user, group_card.id)


def update_group_card(db: Session, user: User, card_id: str, payload: GroupCardUpdate) -> GroupCard:
    group_card = get_group_card(db, user, card_id)
    next_member_id = payload.member_id or group_card.member_id
    _get_active_group_member(db, group_card.group_id, next_member_id)

    normalized_card_number = group_card.card_number
    if payload.card_number is not None:
        normalized_card_number = _normalize_card_number(payload.card_number)
        conflict = _find_group_card_by_number(db, group_card.group_id, normalized_card_number)
        if conflict and conflict.id != group_card.id:
            raise DomainError(code="duplicate_group_card", message="Card number already exists in this group")

    group_card.member_id = next_member_id
    group_card.card_number = normalized_card_number
    if payload.deleted_at is not None:
        group_card.deleted_at = payload.deleted_at
    group_card.updated_at = payload.updated_at or payload.deleted_at or utcnow()
    db.commit()
    db.refresh(group_card)
    return get_group_card(db, user, group_card.id)


def soft_delete_group_card(db: Session, user: User, card_id: str) -> None:
    group_card = get_group_card(db, user, card_id)
    group_card.deleted_at = utcnow()
    group_card.updated_at = group_card.deleted_at
    db.commit()


def list_members(db: Session, user: User, *, group_id: str | None = None) -> list[Member]:
    if group_id:
        group = get_group(db, user, group_id)
        _ensure_active_member_rows(db, group)
        query = select(Member).where(
            Member.group_id == group_id,
            Member.deleted_at.is_(None),
        )
    else:
        groups = list_groups(db, user)
        if not groups:
            return []
        query = select(Member).where(
            Member.group_id.in_([group.id for group in groups]),
            Member.deleted_at.is_(None),
        )
    return list(db.scalars(query.order_by(Member.created_at.asc())))


def get_member(db: Session, user: User, member_id: str) -> Member:
    member = db.scalar(
        select(Member).where(
            Member.id == member_id,
            Member.group_id.in_(_active_group_ids_query(user)),
        )
    )
    if not member:
        raise NotFoundError("Member")
    return member


def _find_member_for_group(db: Session, group_id: str, username: str) -> Member | None:
    return db.scalar(
        select(Member).where(
            Member.group_id == group_id,
            Member.username == username,
            Member.deleted_at.is_(None),
        )
    )


def search_member_suggestions(db: Session, user: User, *, group_id: str, query: str, limit: int = 8) -> list[User]:
    get_group(db, user, group_id)

    normalized_query = query.strip().lower()
    if len(normalized_query) < 3:
        return []

    normalized_limit = max(1, min(limit, 20))
    excluded_user_ids = (
        select(Member.linked_user_id)
        .where(
            Member.group_id == group_id,
            Member.deleted_at.is_(None),
            Member.linked_user_id.is_not(None),
        )
    )
    username_value = func.lower(User.username)
    prefix_rank = case((username_value.startswith(normalized_query), 0), else_=1)

    query_stmt = (
        select(User)
        .where(
            username_value.contains(normalized_query),
            ~User.id.in_(excluded_user_ids),
        )
        .order_by(prefix_rank, User.username.asc())
        .limit(normalized_limit)
    )
    return list(db.scalars(query_stmt))


def _pending_invite_for_member(db: Session, member_id: str) -> GroupInvite | None:
    return db.scalar(
        select(GroupInvite).where(
            GroupInvite.member_id == member_id,
            GroupInvite.status == GroupInviteStatus.PENDING,
        )
    )


def _upsert_member_and_membership(
    db: Session,
    inviter: User,
    payload: MemberCreate,
    *,
    preserve_updated_at: datetime | None = None,
    force_active_connection: bool = False,
) -> AddMemberResult:
    group = get_group(db, inviter, payload.group_id)
    if group.deleted_at is not None:
        raise DomainError(code="invalid_group", message="Cannot add members to a deleted group")

    target_user = _find_user_by_username(db, payload.username)
    if not target_user:
        raise DomainError(code="username_not_found", message="Username does not exist")

    member = _find_member_for_group(db, payload.group_id, target_user.username)
    if member:
        return AddMemberResult(outcome="already_member", member=member)

    membership_status = (
        MembershipStatus.ACTIVE
        if force_active_connection or _is_connected(db, inviter.id, target_user.id)
        else MembershipStatus.PENDING_INVITE
    )
    outcome = "added" if membership_status == MembershipStatus.ACTIVE else "invite_sent"

    member = Member(
        id=_entity_id(payload.id),
        user_id=inviter.id,
        group_id=payload.group_id,
        username=target_user.username,
        linked_user_id=target_user.id,
        membership_status=membership_status,
        is_archived=payload.is_archived,
    )
    db.add(member)
    if preserve_updated_at:
        member.updated_at = preserve_updated_at
    if payload.deleted_at is not None:
        member.deleted_at = payload.deleted_at

    _ensure_group_membership(db, payload.group_id, target_user.id, membership_status)
    if membership_status == MembershipStatus.ACTIVE:
        _ensure_connection(db, inviter.id, target_user.id)
    if membership_status == MembershipStatus.PENDING_INVITE:
        existing_invite = _pending_invite_for_member(db, member.id)
        if not existing_invite:
            db.add(
                GroupInvite(
                    group_id=payload.group_id,
                    inviter_user_id=inviter.id,
                    invitee_user_id=target_user.id,
                    member_id=member.id,
                    status=GroupInviteStatus.PENDING,
                )
            )
    else:
        group.updated_at = preserve_updated_at or utcnow()
    db.commit()
    db.refresh(member)
    return AddMemberResult(outcome=outcome, member=member)


def create_member(db: Session, user: User, payload: MemberCreate, *, preserve_updated_at: datetime | None = None) -> AddMemberResult:
    return _upsert_member_and_membership(db, user, payload, preserve_updated_at=preserve_updated_at)


def create_inline_member(db: Session, user: User, payload: InlineMemberCreateRequest) -> AddMemberResult:
    try:
        create_user_by_inviter(
            db,
            payload=UserCreateByInviter(
                name=payload.name,
                username=payload.username,
                password=payload.password,
            ),
        )
    except DomainError as exc:
        if exc.code != "username_taken":
            raise

    return _upsert_member_and_membership(
        db,
        user,
        MemberCreate(
            group_id=payload.group_id,
            username=payload.username,
            is_archived=payload.is_archived,
        ),
        force_active_connection=True,
    )


def update_member(db: Session, user: User, member_id: str, payload: MemberUpdate) -> Member:
    member = get_member(db, user, member_id)
    if payload.username is not None:
        normalized_username = _normalize_username(payload.username)
        if normalized_username != member.username:
            target_user = _find_user_by_username(db, normalized_username)
            if not target_user:
                raise DomainError(code="username_not_found", message="Username does not exist")
            if member.membership_status == MembershipStatus.ACTIVE and member.linked_user_id not in (None, target_user.id):
                raise DomainError(code="invalid_member_update", message="Cannot retarget an active member")
            conflict = _find_member_for_group(db, member.group_id, normalized_username)
            if conflict and conflict.id != member.id and conflict.deleted_at is None:
                raise DomainError(code="already_member", message="Member is already in the group")
            member.username = normalized_username
            member.linked_user_id = target_user.id
        else:
            target_user = member.linked_user
    else:
        target_user = member.linked_user

    if payload.is_archived is not None:
        member.is_archived = payload.is_archived
    if payload.deleted_at is not None:
        member.deleted_at = payload.deleted_at
    if target_user and member.membership_status == MembershipStatus.PENDING_INVITE:
        pending_invite = _pending_invite_for_member(db, member.id)
        if pending_invite and payload.username is not None:
            pending_invite.invitee_user_id = target_user.id
            pending_invite.updated_at = utcnow()
    member.updated_at = payload.updated_at or payload.deleted_at or utcnow()
    db.commit()
    db.refresh(member)
    return member


def soft_delete_member(db: Session, user: User, member_id: str) -> None:
    member = get_member(db, user, member_id)
    member.deleted_at = utcnow()
    member.updated_at = member.deleted_at
    if member.linked_user_id:
        _delete_group_membership(db, member.group_id, member.linked_user_id)
    pending_invite = _pending_invite_for_member(db, member.id)
    if pending_invite:
        pending_invite.status = GroupInviteStatus.REJECTED
        pending_invite.responded_at = member.deleted_at
        pending_invite.updated_at = member.deleted_at
    db.commit()


def _validate_members_in_group(db: Session, user: User, group_id: str, member_ids: list[str]) -> dict[str, Member]:
    get_group(db, user, group_id)
    requested_members = list(
        db.scalars(
            select(Member).where(
                Member.group_id == group_id,
                Member.id.in_(member_ids),
                Member.deleted_at.is_(None),
            )
        )
    )
    active_members = [member for member in requested_members if member.membership_status == MembershipStatus.ACTIVE]
    member_map = {member.id: member for member in active_members}
    missing = sorted(set(member_ids) - set(member_map))
    pending_members = sorted(
        [member for member in requested_members if member.membership_status == MembershipStatus.PENDING_INVITE],
        key=lambda member: member.username,
    )
    if pending_members:
        pending_usernames = ", ".join(member.username for member in pending_members)
        raise DomainError(
            code="pending_member_invite_acceptance_required",
            message=f"Members must accept the group invite before this action: {pending_usernames}",
            details={
                "pending_members": [
                    {"member_id": member.id, "username": member.username}
                    for member in pending_members
                ]
            },
        )
    if missing:
        raise DomainError(
            code="invalid_member",
            message="One or more members are not available in this group",
            details={"missing_member_ids": missing},
        )
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


def _validate_expense_payload(
    db: Session,
    user: User,
    payload: ExpenseCreate | ExpenseUpdate,
    *,
    group_id: str,
) -> tuple[list[ExpenseParticipantAmount], list[ExpenseParticipantAmount]]:
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
        .where(Expense.group_id.in_(_active_group_ids_query(user)))
        .options(selectinload(Expense.payers), selectinload(Expense.shares))
    )


def list_expenses(db: Session, user: User, *, group_id: str | None = None) -> list[Expense]:
    query = _expense_query(user).where(Expense.deleted_at.is_(None))
    if group_id:
        get_group(db, user, group_id)
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
        payers=payload.payers
        if payload.payers is not None
        else [ExpenseParticipantAmount(member_id=item.member_id, amount=item.amount_paid) for item in expense.payers],
        shares=payload.shares
        if payload.shares is not None
        else [ExpenseParticipantAmount(member_id=item.member_id, amount=item.amount_owed) for item in expense.shares],
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
    query = select(Settlement).where(
        Settlement.group_id.in_(_active_group_ids_query(user)),
        Settlement.deleted_at.is_(None),
    )
    if group_id:
        get_group(db, user, group_id)
        query = query.where(Settlement.group_id == group_id)
    return list(db.scalars(query.order_by(Settlement.created_at.desc())))


def get_settlement(db: Session, user: User, settlement_id: str) -> Settlement:
    settlement = db.scalar(
        select(Settlement).where(
            Settlement.group_id.in_(_active_group_ids_query(user)),
            Settlement.id == settlement_id,
        )
    )
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


def list_group_invites(db: Session, user: User, *, status: GroupInviteStatus | None = GroupInviteStatus.PENDING) -> list[GroupInvite]:
    query = (
        select(GroupInvite)
        .where(GroupInvite.invitee_user_id == user.id)
        .options(
            selectinload(GroupInvite.group),
            selectinload(GroupInvite.member),
            selectinload(GroupInvite.inviter_user),
            selectinload(GroupInvite.invitee_user),
        )
    )
    if status is not None:
        query = query.where(GroupInvite.status == status)
    return list(db.scalars(query.order_by(GroupInvite.created_at.desc())))


def get_group_invite(db: Session, user: User, invite_id: str) -> GroupInvite:
    invite = db.scalar(
        select(GroupInvite)
        .where(
            GroupInvite.id == invite_id,
            GroupInvite.invitee_user_id == user.id,
        )
        .options(
            selectinload(GroupInvite.group),
            selectinload(GroupInvite.member),
            selectinload(GroupInvite.inviter_user),
            selectinload(GroupInvite.invitee_user),
        )
    )
    if not invite:
        raise NotFoundError("Group invite")
    return invite


def accept_group_invite(db: Session, user: User, invite_id: str) -> GroupInvite:
    invite = get_group_invite(db, user, invite_id)
    if invite.status != GroupInviteStatus.PENDING:
        raise DomainError(code="invalid_invite", message="Invite is no longer pending")
    now = utcnow()
    invite.status = GroupInviteStatus.ACCEPTED
    invite.responded_at = now
    invite.updated_at = now
    invite.member.membership_status = MembershipStatus.ACTIVE
    invite.member.linked_user_id = user.id
    invite.member.updated_at = now
    invite.group.updated_at = now
    _ensure_group_membership(db, invite.group_id, user.id, MembershipStatus.ACTIVE)
    _ensure_connection(db, invite.inviter_user_id, user.id)
    db.commit()
    _ensure_active_member_rows(db, invite.group)
    db.refresh(invite)
    return get_group_invite(db, user, invite.id)


def reject_group_invite(db: Session, user: User, invite_id: str) -> GroupInvite:
    invite = get_group_invite(db, user, invite_id)
    if invite.status != GroupInviteStatus.PENDING:
        raise DomainError(code="invalid_invite", message="Invite is no longer pending")
    now = utcnow()
    invite.status = GroupInviteStatus.REJECTED
    invite.responded_at = now
    invite.updated_at = now
    invite.member.deleted_at = now
    invite.member.updated_at = now
    _delete_group_membership(db, invite.group_id, user.id)
    db.commit()
    db.refresh(invite)
    return get_group_invite(db, user, invite.id)


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
        _active_group_query(user)
        .where(Group.id == group_id)
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
        (
            member
            for member in group.members
            if member.deleted_at is None and member.membership_status == MembershipStatus.ACTIVE
        ),
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
                member_name=member.username,
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
