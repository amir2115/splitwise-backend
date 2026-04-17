from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models.domain import GroupInviteStatus, MembershipStatus, SplitType
from app.schemas.common import TimestampedResponse


class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupCreate(GroupBase):
    id: str | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class GroupResponse(TimestampedResponse):
    name: str
    user_id: str


class GroupCardBase(BaseModel):
    group_id: str
    member_id: str
    card_number: str = Field(min_length=16, max_length=32)


class GroupCardCreate(GroupCardBase):
    id: str | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class GroupCardUpdate(BaseModel):
    member_id: str | None = None
    card_number: str | None = Field(default=None, min_length=16, max_length=32)
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class GroupCardResponse(TimestampedResponse):
    group_id: str
    member_id: str
    card_number: str
    user_id: str


class MemberBase(BaseModel):
    group_id: str
    username: str = Field(min_length=3, max_length=64)
    is_archived: bool = False


class MemberCreate(MemberBase):
    id: str | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class InlineMemberCreateRequest(BaseModel):
    group_id: str
    name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=255)
    is_archived: bool = False


class MemberUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    is_archived: bool | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class MemberResponse(TimestampedResponse):
    group_id: str
    username: str
    membership_status: MembershipStatus
    is_archived: bool
    user_id: str | None


class MemberSuggestionResponse(BaseModel):
    id: str
    username: str
    name: str | None


class AddMemberResponse(BaseModel):
    outcome: Literal["added", "invite_sent", "already_member"]
    member: MemberResponse


class GroupInviteResponse(TimestampedResponse):
    group_id: str
    group_name: str
    member_id: str
    username: str
    inviter_user_id: str
    inviter_username: str
    invitee_user_id: str
    invitee_username: str
    status: GroupInviteStatus
    responded_at: datetime | None


class ExpenseParticipantAmount(BaseModel):
    member_id: str
    amount: int = Field(ge=0)


class ExpenseBase(BaseModel):
    group_id: str
    title: str = Field(min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=1000)
    total_amount: int = Field(gt=0)
    split_type: SplitType
    payers: list[ExpenseParticipantAmount]
    shares: list[ExpenseParticipantAmount]

    @model_validator(mode="after")
    def check_lists(self) -> "ExpenseBase":
        if not self.payers:
            raise ValueError("at least one payer is required")
        if not self.shares:
            raise ValueError("at least one share is required")
        return self


class ExpenseCreate(ExpenseBase):
    id: str | None = None
    updated_at: datetime | None = None


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=1000)
    total_amount: int | None = Field(default=None, gt=0)
    split_type: SplitType | None = None
    payers: list[ExpenseParticipantAmount] | None = None
    shares: list[ExpenseParticipantAmount] | None = None
    deleted_at: datetime | None = None
    updated_at: datetime | None = None


class ExpenseResponse(TimestampedResponse):
    group_id: str
    title: str
    note: str | None
    total_amount: int
    split_type: SplitType
    user_id: str
    payers: list[ExpenseParticipantAmount]
    shares: list[ExpenseParticipantAmount]


class SettlementBase(BaseModel):
    group_id: str
    from_member_id: str
    to_member_id: str
    amount: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=1000)


class SettlementCreate(SettlementBase):
    id: str | None = None
    updated_at: datetime | None = None


class SettlementUpdate(BaseModel):
    from_member_id: str | None = None
    to_member_id: str | None = None
    amount: int | None = Field(default=None, gt=0)
    note: str | None = Field(default=None, max_length=1000)
    deleted_at: datetime | None = None
    updated_at: datetime | None = None


class SettlementResponse(TimestampedResponse):
    group_id: str
    from_member_id: str
    to_member_id: str
    amount: int
    note: str | None
    user_id: str


class MemberBalance(BaseModel):
    member_id: str
    member_name: str
    paid_total: int
    owed_total: int
    net_balance: int


class SimplifiedDebt(BaseModel):
    from_member_id: str
    to_member_id: str
    amount: int


class GroupBalanceResponse(BaseModel):
    group_id: str
    balances: list[MemberBalance]
    simplified_debts: list[SimplifiedDebt]
