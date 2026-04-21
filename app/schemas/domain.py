from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from app.models.domain import GroupInviteStatus, MembershipStatus, SplitType
from app.schemas.common import TimestampedResponse


class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class GroupCreate(GroupBase):
    id: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class GroupResponse(TimestampedResponse):
    name: str
    user_id: str


class GroupCardBase(BaseModel):
    group_id: str
    member_id: str
    card_number: str = Field(min_length=16, max_length=32)


class GroupCardCreate(GroupCardBase):
    id: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class GroupCardUpdate(BaseModel):
    member_id: Optional[str] = None
    card_number: Optional[str] = Field(default=None, min_length=16, max_length=32)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


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
    id: Optional[str] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class InlineMemberCreateRequest(BaseModel):
    group_id: str
    name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=255)
    phone_number: Optional[str] = None
    is_archived: bool = False


class MemberUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=64)
    is_archived: Optional[bool] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class MemberResponse(TimestampedResponse):
    group_id: str
    username: str
    membership_status: MembershipStatus
    is_archived: bool
    user_id: Optional[str]


class MemberSuggestionResponse(BaseModel):
    id: str
    username: str
    name: Optional[str]


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
    responded_at: Optional[datetime]


class ExpenseParticipantAmount(BaseModel):
    member_id: str
    amount: int = Field(ge=0)


class ExpenseBase(BaseModel):
    group_id: str
    title: str = Field(min_length=1, max_length=255)
    note: Optional[str] = Field(default=None, max_length=1000)
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
    id: Optional[str] = None
    updated_at: Optional[datetime] = None


class ExpenseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    note: Optional[str] = Field(default=None, max_length=1000)
    total_amount: Optional[int] = Field(default=None, gt=0)
    split_type: Optional[SplitType] = None
    payers: Optional[list[ExpenseParticipantAmount]] = None
    shares: Optional[list[ExpenseParticipantAmount]] = None
    deleted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExpenseResponse(TimestampedResponse):
    group_id: str
    title: str
    note: Optional[str]
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
    note: Optional[str] = Field(default=None, max_length=1000)


class SettlementCreate(SettlementBase):
    id: Optional[str] = None
    updated_at: Optional[datetime] = None


class SettlementUpdate(BaseModel):
    from_member_id: Optional[str] = None
    to_member_id: Optional[str] = None
    amount: Optional[int] = Field(default=None, gt=0)
    note: Optional[str] = Field(default=None, max_length=1000)
    deleted_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SettlementResponse(TimestampedResponse):
    group_id: str
    from_member_id: str
    to_member_id: str
    amount: int
    note: Optional[str]
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
