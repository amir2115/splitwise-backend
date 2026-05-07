from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.articles import ArticleDetailResponse, ArticleListResponse, CategoriesResponse, SitemapArticlesResponse
from app.services.articles_service import build_articles_sitemap, get_public_article, list_articles, list_categories

router = APIRouter()


@router.get("", response_model=ArticleListResponse)
def public_list_articles(
    category: Optional[str] = Query(default=None),
    cursor: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> ArticleListResponse:
    return list_articles(db, category=category, cursor=cursor, limit=limit)


@router.get("/categories", response_model=CategoriesResponse)
def public_list_article_categories(db: Session = Depends(get_db)) -> CategoriesResponse:
    return list_categories(db)


@router.get("/sitemap", response_model=SitemapArticlesResponse)
def public_articles_sitemap(db: Session = Depends(get_db)) -> SitemapArticlesResponse:
    return build_articles_sitemap(db)


@router.get("/{slug}", response_model=ArticleDetailResponse)
def public_get_article(
    slug: str = Path(...),
    db: Session = Depends(get_db),
) -> ArticleDetailResponse:
    return get_public_article(db, slug)
