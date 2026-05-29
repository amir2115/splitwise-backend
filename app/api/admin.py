from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Path, Query, Request, UploadFile
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
from app.schemas.articles import (
    AdminArticleDetailResponse,
    AdminArticleExportResponse,
    AdminArticleListResponse,
    ArticleAuthorResponse,
    ArticleImageUploadResponse,
    ArticlePatchRequest,
    ArticleWriteRequest,
    AuthorWriteRequest,
    CategoryWriteRequest,
    ArticleCategoryResponse,
)
from app.services.admin_service import authenticate_admin, build_admin_session, delete_user, get_runtime_settings, list_users, update_runtime_settings, update_user
from app.services.articles_service import (
    archive_article,
    create_article,
    create_author,
    create_category,
    export_admin_articles,
    get_admin_article,
    get_admin_article_by_slug,
    list_admin_articles,
    publish_article,
    update_article,
    upload_article_hero_image,
)

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
    client_platform: Optional[Literal["android", "frontend", "unknown"]] = Query(default=None),
    android_variant: Optional[Literal["bazaar", "myket", "organic", "unknown"]] = Query(default=None),
    sort_by: Literal[
        "created_at",
        "updated_at",
        "name",
        "username",
        "groups_count",
        "active_refresh_tokens_count",
        "has_phone_number",
        "is_phone_verified",
        "client_platform",
        "android_variant",
        "last_client_seen_at",
    ] = Query(default="created_at"),
    sort_order: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminUserListResponse:
    query = AdminUsersQuery(
        search=search,
        must_change_password=must_change_password,
        client_platform=client_platform,
        android_variant=android_variant,
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


@router.post("/categories", response_model=ArticleCategoryResponse, status_code=201)
def admin_create_article_category(
    payload: CategoryWriteRequest,
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> ArticleCategoryResponse:
    return create_category(db, payload)


@router.post("/authors", response_model=ArticleAuthorResponse, status_code=201)
def admin_create_article_author(
    payload: AuthorWriteRequest,
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> ArticleAuthorResponse:
    return create_author(db, payload)


@router.post("/articles", response_model=AdminArticleDetailResponse, status_code=201)
def admin_create_article(
    payload: ArticleWriteRequest,
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminArticleDetailResponse:
    return create_article(db, payload)


@router.get("/articles", response_model=AdminArticleListResponse)
def admin_list_articles(
    search: Optional[str] = Query(default=None),
    status: Optional[Literal["draft", "published", "archived"]] = Query(default=None),
    category: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminArticleListResponse:
    return list_admin_articles(db, search=search, status_filter=status, category=category, page=page, page_size=page_size)


@router.get("/articles/export", response_model=AdminArticleExportResponse)
def admin_export_articles(
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminArticleExportResponse:
    return export_admin_articles(db)


@router.get("/articles/slug/{slug}", response_model=AdminArticleDetailResponse)
def admin_get_article_by_slug(
    slug: str = Path(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminArticleDetailResponse:
    return get_admin_article_by_slug(db, slug)


@router.get("/articles/{article_id}", response_model=AdminArticleDetailResponse)
def admin_get_article(
    article_id: str = Path(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminArticleDetailResponse:
    return get_admin_article(db, article_id)


@router.patch("/articles/{article_id}", response_model=AdminArticleDetailResponse)
def admin_update_article(
    payload: ArticlePatchRequest,
    article_id: str = Path(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminArticleDetailResponse:
    return update_article(db, article_id, payload)


@router.post("/articles/{article_id}/publish", response_model=AdminArticleDetailResponse)
def admin_publish_article(
    article_id: str = Path(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> AdminArticleDetailResponse:
    return publish_article(db, article_id)


@router.post("/articles/{article_id}/hero-image", response_model=ArticleImageUploadResponse)
async def admin_upload_article_hero_image(
    article_id: str = Path(...),
    file: UploadFile = File(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> ArticleImageUploadResponse:
    content = await file.read()
    return upload_article_hero_image(db, article_id, filename=file.filename, content=content)


@router.delete("/articles/{article_id}", status_code=204)
def admin_archive_article(
    article_id: str = Path(...),
    _: str = Depends(get_current_admin_username),
    db: Session = Depends(get_db),
) -> None:
    archive_article(db, article_id)
