from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import DomainError
from app.core.config import get_settings
from app.core.time import utcnow
from app.models.domain import Article, ArticleAuthor, ArticleCategory, ArticleRedirect, ArticleStatus
from app.schemas.articles import (
    ArticleAuthorResponse,
    ArticleCategoryResponse,
    ArticleDetailResponse,
    ArticleImageUploadResponse,
    ArticleListItem,
    ArticleListResponse,
    ArticlePatchRequest,
    ArticleSection,
    ArticleSeoResponse,
    ArticleWriteRequest,
    AuthorWriteRequest,
    CategoriesResponse,
    CategoryWriteRequest,
    RelatedArticleResponse,
    SitemapArticleItem,
    SitemapArticlesResponse,
)


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: Optional[str]) -> int:
    if not cursor:
        return 0
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        return max(int(decoded), 0)
    except (ValueError, UnicodeDecodeError):
        raise DomainError(code="invalid_cursor", message="Invalid article cursor", status_code=status.HTTP_400_BAD_REQUEST)


def _build_toc(body: list[dict]) -> list[dict]:
    return [
        {"id": block["id"], "title": block["text"]}
        for block in body
        if block.get("kind") == "heading"
    ]


def _category_response(category: ArticleCategory, *, count: int | None = None) -> ArticleCategoryResponse:
    return ArticleCategoryResponse(
        slug=category.slug,
        name=category.name,
        description=category.description,
        display_order=category.display_order,
        count=count,
    )


def _author_response(author: ArticleAuthor) -> ArticleAuthorResponse:
    return ArticleAuthorResponse(
        slug=author.slug,
        name=author.name,
        role=author.role,
        bio=author.bio,
        avatar_url=author.avatar_url,
    )


def _seo_response(article: Article) -> ArticleSeoResponse:
    return ArticleSeoResponse(
        meta_title=article.meta_title,
        meta_description=article.meta_description,
        canonical_url=article.canonical_url,
        og_image_url=article.og_image_url,
    )


def _list_item(article: Article) -> ArticleListItem:
    return ArticleListItem(
        id=article.id,
        slug=article.slug,
        title=article.title,
        summary=article.summary,
        category=_category_response(article.category),
        author=_author_response(article.author),
        reading_minutes=article.reading_minutes,
        hero_icon=article.hero_icon,
        hero_image_url=article.hero_image_url,
        status=article.status.value,
        published_at=article.published_at,
        updated_at=article.updated_at,
    )


def _find_category(db: Session, slug: str) -> ArticleCategory:
    category = db.scalar(select(ArticleCategory).where(ArticleCategory.slug == slug))
    if not category:
        raise DomainError(code="article_category_not_found", message="Article category not found", status_code=status.HTTP_404_NOT_FOUND)
    return category


def _find_author(db: Session, slug: str) -> ArticleAuthor:
    author = db.scalar(select(ArticleAuthor).where(ArticleAuthor.slug == slug))
    if not author:
        raise DomainError(code="article_author_not_found", message="Article author not found", status_code=status.HTTP_404_NOT_FOUND)
    return author


def _find_article_by_id(db: Session, article_id: str) -> Article:
    article = db.scalar(
        select(Article)
        .options(joinedload(Article.category), joinedload(Article.author))
        .where(Article.id == article_id)
    )
    if not article:
        raise DomainError(code="article_not_found", message="Article not found", status_code=status.HTTP_404_NOT_FOUND)
    return article


def _ensure_slug_available(db: Session, slug: str, *, current_id: str | None = None) -> None:
    existing = db.scalar(select(Article).where(Article.slug == slug))
    if existing and existing.id != current_id:
        raise DomainError(code="article_slug_taken", message="Article slug is already used", status_code=status.HTTP_409_CONFLICT)


def _ensure_related_exist(db: Session, related_slugs: list[str], *, own_slug: str) -> None:
    if own_slug in related_slugs:
        raise DomainError(code="article_related_self", message="Article cannot be related to itself", status_code=status.HTTP_400_BAD_REQUEST)
    if not related_slugs:
        return
    rows = db.scalars(select(Article.slug).where(Article.slug.in_(related_slugs))).all()
    missing = sorted(set(related_slugs) - set(rows))
    if missing:
        raise DomainError(
            code="article_related_not_found",
            message="One or more related articles do not exist",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"slugs": missing},
        )


def _apply_write_payload(db: Session, article: Article, payload: ArticleWriteRequest | ArticlePatchRequest) -> Article:
    values = payload.model_dump(exclude_unset=True)

    if "category_slug" in values:
        article.category = _find_category(db, values["category_slug"])
    if "author_slug" in values:
        article.author = _find_author(db, values["author_slug"])
    if "slug" in values:
        _ensure_slug_available(db, values["slug"], current_id=article.id)
        if article.slug and article.slug != values["slug"]:
            db.add(ArticleRedirect(from_slug=article.slug, to_slug=values["slug"]))
        article.slug = values["slug"]

    for field in ("title", "summary", "tldr", "hero_icon", "hero_image_url", "reading_minutes", "audience", "related_slugs"):
        if field in values:
            setattr(article, field, values[field])

    if "body" in values:
        body = values["body"]
        article.body = body
        article.toc = _build_toc(body)

    if "seo" in values:
        seo = values["seo"] or {}
        for source, target in (
            ("meta_title", "meta_title"),
            ("meta_description", "meta_description"),
            ("canonical_url", "canonical_url"),
            ("og_image_url", "og_image_url"),
        ):
            if source in seo:
                setattr(article, target, seo[source])

    if "published_at" in values:
        article.published_at = values["published_at"]

    if "status" in values:
        article.status = ArticleStatus(values["status"])
        if article.status == ArticleStatus.PUBLISHED and not article.published_at:
            article.published_at = utcnow()
        if article.status == ArticleStatus.ARCHIVED and not article.archived_at:
            article.archived_at = utcnow()
    return article


def create_category(db: Session, payload: CategoryWriteRequest) -> ArticleCategoryResponse:
    existing = db.scalar(select(ArticleCategory).where(ArticleCategory.slug == payload.slug))
    if existing:
        raise DomainError(code="article_category_slug_taken", message="Article category slug is already used", status_code=status.HTTP_409_CONFLICT)
    category = ArticleCategory(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return _category_response(category)


def create_author(db: Session, payload: AuthorWriteRequest) -> ArticleAuthorResponse:
    existing = db.scalar(select(ArticleAuthor).where(ArticleAuthor.slug == payload.slug))
    if existing:
        raise DomainError(code="article_author_slug_taken", message="Article author slug is already used", status_code=status.HTTP_409_CONFLICT)
    author = ArticleAuthor(**payload.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)
    return _author_response(author)


def create_article(db: Session, payload: ArticleWriteRequest) -> ArticleDetailResponse:
    _ensure_slug_available(db, payload.slug)
    _ensure_related_exist(db, payload.related_slugs, own_slug=payload.slug)
    article = Article(
        slug=payload.slug,
        title=payload.title,
        summary=payload.summary,
        tldr=payload.tldr,
        hero_icon=payload.hero_icon,
        hero_image_url=payload.hero_image_url,
        reading_minutes=payload.reading_minutes,
        body=[block.model_dump() for block in payload.body],
        toc=[],
        audience=payload.audience,
        related_slugs=payload.related_slugs,
        meta_title=payload.seo.meta_title,
        meta_description=payload.seo.meta_description,
        canonical_url=payload.seo.canonical_url,
        og_image_url=payload.seo.og_image_url,
        status=ArticleStatus(payload.status),
        published_at=payload.published_at,
        category=_find_category(db, payload.category_slug),
        author=_find_author(db, payload.author_slug),
    )
    article.toc = _build_toc(article.body)
    if article.status == ArticleStatus.PUBLISHED and not article.published_at:
        article.published_at = utcnow()
    if article.status == ArticleStatus.ARCHIVED:
        article.archived_at = utcnow()
    db.add(article)
    db.commit()
    db.refresh(article)
    return get_admin_article(db, article.id)


def update_article(db: Session, article_id: str, payload: ArticlePatchRequest) -> ArticleDetailResponse:
    article = _find_article_by_id(db, article_id)
    next_slug = payload.slug or article.slug
    next_related = payload.related_slugs if payload.related_slugs is not None else article.related_slugs
    _ensure_related_exist(db, next_related, own_slug=next_slug)
    _apply_write_payload(db, article, payload)
    db.commit()
    db.refresh(article)
    return get_admin_article(db, article.id)


def publish_article(db: Session, article_id: str) -> ArticleDetailResponse:
    article = _find_article_by_id(db, article_id)
    article.status = ArticleStatus.PUBLISHED
    if not article.published_at:
        article.published_at = utcnow()
    db.commit()
    db.refresh(article)
    return get_admin_article(db, article.id)


def archive_article(db: Session, article_id: str) -> None:
    article = _find_article_by_id(db, article_id)
    article.status = ArticleStatus.ARCHIVED
    article.archived_at = utcnow()
    db.commit()


ALLOWED_ARTICLE_IMAGE_EXTENSIONS = {".webp", ".png", ".jpg", ".jpeg"}


def upload_article_hero_image(db: Session, article_id: str, *, filename: str | None, content: bytes) -> ArticleImageUploadResponse:
    if not filename:
        raise DomainError(code="invalid_article_image", message="Article image file is required")
    safe_name = Path(filename).name
    if safe_name != filename:
        raise DomainError(code="invalid_article_image", message="Invalid article image filename")
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_ARTICLE_IMAGE_EXTENSIONS:
        raise DomainError(code="invalid_article_image", message="Only .webp, .png, .jpg and .jpeg files are supported")
    if not content:
        raise DomainError(code="invalid_article_image", message="Article image file is empty")

    article = _find_article_by_id(db, article_id)
    settings = get_settings()
    upload_dir = Path(settings.article_image_upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{article.slug}{extension}"
    stored_path = upload_dir / stored_filename
    stored_path.write_bytes(content)

    base_url = settings.article_image_public_base_url.rstrip("/") + "/"
    hero_image_url = urljoin(base_url, f"files/articles/{stored_filename}")
    article.hero_image_url = hero_image_url
    if not article.og_image_url:
        article.og_image_url = hero_image_url
    db.commit()

    return ArticleImageUploadResponse(
        filename=stored_filename,
        stored_path=str(stored_path),
        hero_image_url=hero_image_url,
    )


def list_articles(db: Session, *, category: str | None, cursor: str | None, limit: int, include_unpublished: bool = False) -> ArticleListResponse:
    offset = _decode_cursor(cursor)
    query = select(Article).options(joinedload(Article.category), joinedload(Article.author))
    if not include_unpublished:
        query = query.where(Article.status == ArticleStatus.PUBLISHED)
    if category:
        query = query.join(Article.category).where(ArticleCategory.slug == category)
    query = query.order_by(Article.published_at.desc().nullslast(), Article.updated_at.desc()).offset(offset).limit(limit + 1)
    rows = list(db.scalars(query).all())
    has_next = len(rows) > limit
    items = rows[:limit]
    return ArticleListResponse(
        items=[_list_item(article) for article in items],
        next_cursor=_encode_cursor(offset + limit) if has_next else None,
    )


def _article_detail(db: Session, article: Article) -> ArticleDetailResponse:
    related_rows = []
    if article.related_slugs:
        related_rows = list(
            db.scalars(
                select(Article)
                .options(joinedload(Article.category), joinedload(Article.author))
                .where(Article.slug.in_(article.related_slugs), Article.status == ArticleStatus.PUBLISHED)
            ).all()
        )
    related_by_slug = {item.slug: item for item in related_rows}
    related = [
        RelatedArticleResponse(
            slug=related_article.slug,
            title=related_article.title,
            excerpt=related_article.summary,
            category=related_article.category.name,
            reading_minutes=related_article.reading_minutes,
        )
        for slug in article.related_slugs
        if (related_article := related_by_slug.get(slug))
    ]
    list_item = _list_item(article)
    return ArticleDetailResponse(
        **list_item.model_dump(),
        tldr=article.tldr,
        body=article.body,
        toc=[ArticleSection(**item) for item in article.toc],
        audience=article.audience,
        related=related,
        seo=_seo_response(article),
    )


def get_admin_article(db: Session, article_id: str) -> ArticleDetailResponse:
    return _article_detail(db, _find_article_by_id(db, article_id))


def get_public_article(db: Session, slug: str) -> ArticleDetailResponse:
    article = db.scalar(
        select(Article)
        .options(joinedload(Article.category), joinedload(Article.author))
        .where(Article.slug == slug)
    )
    if not article:
        redirect = db.scalar(select(ArticleRedirect).where(ArticleRedirect.from_slug == slug))
        if redirect:
            raise DomainError(
                code="article_redirected",
                message="Article moved",
                status_code=status.HTTP_301_MOVED_PERMANENTLY,
                details={"redirect_to": redirect.to_slug},
            )
        raise DomainError(code="article_not_found", message="Article not found", status_code=status.HTTP_404_NOT_FOUND)
    if article.status == ArticleStatus.ARCHIVED:
        raise DomainError(code="article_archived", message="Article archived", status_code=status.HTTP_410_GONE)
    if article.status != ArticleStatus.PUBLISHED:
        raise DomainError(code="article_not_found", message="Article not found", status_code=status.HTTP_404_NOT_FOUND)
    return _article_detail(db, article)


def list_categories(db: Session) -> CategoriesResponse:
    published_counts = (
        select(Article.category_id.label("category_id"), func.count(Article.id).label("count"))
        .where(Article.status == ArticleStatus.PUBLISHED)
        .group_by(Article.category_id)
        .subquery()
    )
    rows = db.execute(
        select(ArticleCategory, func.coalesce(published_counts.c.count, 0))
        .outerjoin(published_counts, published_counts.c.category_id == ArticleCategory.id)
        .order_by(ArticleCategory.display_order.asc(), ArticleCategory.name.asc())
    ).all()
    return CategoriesResponse(items=[_category_response(category, count=int(count or 0)) for category, count in rows])


def build_articles_sitemap(db: Session) -> SitemapArticlesResponse:
    rows = db.scalars(
        select(Article)
        .where(Article.status == ArticleStatus.PUBLISHED)
        .order_by(Article.published_at.desc().nullslast(), Article.updated_at.desc())
    ).all()
    return SitemapArticlesResponse(
        items=[
            SitemapArticleItem(
                slug=article.slug,
                updated_at=article.updated_at,
            )
            for article in rows
        ]
    )
