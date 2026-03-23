from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.domain import ExpenseCreate, GroupCreate, MemberCreate, SettlementCreate


class SyncCursor(BaseModel):
    last_synced_at: datetime | None = None


class SyncPayload(BaseModel):
    device_id: str = Field(min_length=1, max_length=255)
    groups: list[GroupCreate] = Field(default_factory=list)
    members: list[MemberCreate] = Field(default_factory=list)
    expenses: list[ExpenseCreate] = Field(default_factory=list)
    settlements: list[SettlementCreate] = Field(default_factory=list)
    deleted_group_ids: list[str] = Field(default_factory=list)
    deleted_member_ids: list[str] = Field(default_factory=list)
    deleted_expense_ids: list[str] = Field(default_factory=list)
    deleted_settlement_ids: list[str] = Field(default_factory=list)


class SyncRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=255)
    last_synced_at: datetime | None = None
    push: SyncPayload | None = None


class SyncPullResponse(BaseModel):
    groups: list[dict]
    members: list[dict]
    expenses: list[dict]
    settlements: list[dict]
    deleted_group_ids: list[str]
    deleted_member_ids: list[str]
    deleted_expense_ids: list[str]
    deleted_settlement_ids: list[str]


class SyncResponse(BaseModel):
    server_time: datetime
    next_cursor: datetime
    changes: SyncPullResponse


class InitialImportRequest(SyncPayload):
    pass
