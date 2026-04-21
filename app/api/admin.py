from typing import Literal, Optional

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy.orm import Session

from app.admin.dependencies import get_current_admin_username
from app.db.session import get_db
from app.schemas.admin import (
    AdminAuthResponse,
    AdminResponse,
    AdminLoginRequest,
    AdminRuntimeSettingsResponse,
    AdminRuntimeSettingsUpdateRequest,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserUpdateRequest,
    AdminUsersQuery,
)
from app.services.admin_service import authenticate_admin, build_admin_session, delete_user, get_runtime_settings, list_users, update_runtime_settings, update_user

router = APIRouter()


@router.post("/auth/login", response_model=AdminAuthResponse)
def admin_login(payload: AdminLoginRequest, request: Request) -> AdminAuthResponse:
    client_host = request.client.host if request.client else "unknown"
    return authenticate_admin(payload.username, payload.password, client_host)


@router.get("/auth/me", response_model=AdminResponse)
def admin_me(admin_username: str = Depends(get_current_admin_username)) -> AdminResponse:
    return build_admin_session(admin_username)


@router.get("/users", response_model=AdminUserListResponse)
def admin_list_users(
    search: Optional[str] = Query(default=None),
    must_change_password: Optional[bool] = Query(default=None),
    sort_by: Literal["created_at", "updated_at", "name", "username", "groups_count", "active_refresh_tokens_count"] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    query = AdminUsersQuery(
        search=search,
        must_change_password=must_change_password,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return list_users(db, query)


@router.patch("/users/{user_id}", response_model=AdminUserListItem)
def admin_update_user(
    payload: AdminUserUpdateRequest,
    user_id: str = Path(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminUserListItem:
    return update_user(db, user_id=user_id, payload=payload)


@router.delete("/users/{user_id}", status_code=204)
def admin_delete_user(
    user_id: str = Path(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> None:
    delete_user(db, user_id=user_id)


@router.get("/settings/runtime", response_model=AdminRuntimeSettingsResponse)
def admin_get_runtime_settings(
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminRuntimeSettingsResponse:
    return get_runtime_settings(db)


@router.patch("/settings/runtime", response_model=AdminRuntimeSettingsResponse)
def admin_patch_runtime_settings(
    payload: AdminRuntimeSettingsUpdateRequest,
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminRuntimeSettingsResponse:
    return update_runtime_settings(db, payload)
