from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Optional, Union
import re

from pydantic import BaseModel, Field, field_validator, model_validator


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class LinkPayload(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    href: str = Field(min_length=1, max_length=500)


class ArticleSection(BaseModel):
    id: str
    title: str


class HeadingBlock(BaseModel):
    kind: Literal["heading"]
    level: Literal[2, 3]
    id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=220)
    eyebrow: Optional[str] = Field(default=None, max_length=32)

    @field_validator("id")
    @classmethod
    def validate_heading_id(cls, value: str) -> str:
        if not SLUG_RE.fullmatch(value):
            raise ValueError("heading id must contain lowercase letters, numbers and hyphens only")
        return value


class ProseBlock(BaseModel):
    kind: Literal["prose"]
    paragraphs: list[str] = Field(min_length=1)


class ListBlock(BaseModel):
    kind: Literal["list"]
    ordered: bool = False
    items: list[str] = Field(min_length=1)


class CalloutBlock(BaseModel):
    kind: Literal["callout"]
    variant: Literal["tip", "warning", "note", "highlight"]
    title: Optional[str] = Field(default=None, max_length=180)
    body: str = Field(min_length=1)


class ScenarioRow(BaseModel):
    label: str = Field(min_length=1, max_length=180)
    value: str = Field(min_length=1, max_length=180)
    hint: Optional[str] = Field(default=None, max_length=180)


class ScenarioSummary(BaseModel):
    label: str = Field(min_length=1, max_length=180)
    value: str = Field(min_length=1, max_length=180)


class ScenarioBlock(BaseModel):
    kind: Literal["scenario"]
    title: str = Field(min_length=1, max_length=220)
    intro: Optional[str] = None
    rows: list[ScenarioRow] = Field(min_length=1)
    summary: Optional[ScenarioSummary] = None
    footnote: Optional[str] = None


class ComparisonOption(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    tag: Optional[str] = Field(default=None, max_length=80)
    pros: list[str] = Field(min_length=1)
    cons: list[str] = Field(default_factory=list)
    recommended: bool = False


class ComparisonBlock(BaseModel):
    kind: Literal["comparison"]
    title: str = Field(min_length=1, max_length=220)
    intro: Optional[str] = None
    options: list[ComparisonOption] = Field(min_length=1)


class StepItem(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1)


class StepsBlock(BaseModel):
    kind: Literal["steps"]
    title: Optional[str] = Field(default=None, max_length=220)
    steps: list[StepItem] = Field(min_length=1)


class InlineCtaBlock(BaseModel):
    kind: Literal["inline-cta"]
    variant: Literal["soft", "strong"]
    title: str = Field(min_length=1, max_length=220)
    body: Optional[str] = None
    primary: LinkPayload
    secondary: Optional[LinkPayload] = None


class FaqItem(BaseModel):
    question: str = Field(min_length=1, max_length=260)
    answer: str = Field(min_length=1)


class FaqBlock(BaseModel):
    kind: Literal["faq"]
    title: str = Field(min_length=1, max_length=220)
    items: list[FaqItem] = Field(min_length=1)


ContentBlock = Annotated[
    Union[
        HeadingBlock,
        ProseBlock,
        ListBlock,
        CalloutBlock,
        ScenarioBlock,
        ComparisonBlock,
        StepsBlock,
        InlineCtaBlock,
        FaqBlock,
    ],
    Field(discriminator="kind"),
]


class ArticleSeoPayload(BaseModel):
    meta_title: Optional[str] = Field(default=None, max_length=220)
    meta_description: Optional[str] = Field(default=None, max_length=320)
    canonical_url: Optional[str] = Field(default=None, max_length=500)
    og_image_url: Optional[str] = Field(default=None, max_length=500)


class ArticleWriteRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    status: Literal["draft", "published", "archived"] = "draft"
    category_slug: str = Field(min_length=1, max_length=80)
    author_slug: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=220)
    summary: str = Field(min_length=1)
    tldr: str = Field(min_length=1)
    hero_icon: str = Field(default="✦", min_length=1, max_length=16)
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    reading_minutes: int = Field(default=5, ge=1, le=120)
    published_at: Optional[datetime] = None
    audience: list[str] = Field(default_factory=list)
    body: list[ContentBlock] = Field(min_length=1)
    related_slugs: list[str] = Field(default_factory=list)
    seo: ArticleSeoPayload = Field(default_factory=ArticleSeoPayload)

    @field_validator("slug", "category_slug", "author_slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not SLUG_RE.fullmatch(value):
            raise ValueError("slug must contain lowercase letters, numbers and hyphens only")
        return value

    @field_validator("related_slugs")
    @classmethod
    def validate_related_slugs(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        for slug in value:
            if not SLUG_RE.fullmatch(slug):
                raise ValueError("related slugs must contain lowercase letters, numbers and hyphens only")
            if slug in seen:
                raise ValueError("related slugs must be unique")
            seen.add(slug)
        return value

    @model_validator(mode="after")
    def validate_article_shape(self) -> "ArticleWriteRequest":
        heading_ids: set[str] = set()
        for block in self.body:
            if isinstance(block, HeadingBlock):
                if block.id in heading_ids:
                    raise ValueError(f"duplicate heading id: {block.id}")
                heading_ids.add(block.id)
        if self.slug in self.related_slugs:
            raise ValueError("article cannot be related to itself")
        return self


class ArticlePatchRequest(BaseModel):
    slug: Optional[str] = Field(default=None, min_length=1, max_length=120)
    status: Optional[Literal["draft", "published", "archived"]] = None
    category_slug: Optional[str] = Field(default=None, min_length=1, max_length=80)
    author_slug: Optional[str] = Field(default=None, min_length=1, max_length=80)
    title: Optional[str] = Field(default=None, min_length=1, max_length=220)
    summary: Optional[str] = Field(default=None, min_length=1)
    tldr: Optional[str] = Field(default=None, min_length=1)
    hero_icon: Optional[str] = Field(default=None, min_length=1, max_length=16)
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    reading_minutes: Optional[int] = Field(default=None, ge=1, le=120)
    published_at: Optional[datetime] = None
    audience: Optional[list[str]] = None
    body: Optional[list[ContentBlock]] = Field(default=None, min_length=1)
    related_slugs: Optional[list[str]] = None
    seo: Optional[ArticleSeoPayload] = None

    @field_validator("slug", "category_slug", "author_slug")
    @classmethod
    def validate_optional_slug(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not SLUG_RE.fullmatch(value):
            raise ValueError("slug must contain lowercase letters, numbers and hyphens only")
        return value

    @field_validator("related_slugs")
    @classmethod
    def validate_optional_related_slugs(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return value
        return ArticleWriteRequest.validate_related_slugs(value)

    @model_validator(mode="after")
    def validate_patch_shape(self) -> "ArticlePatchRequest":
        if self.body is not None:
            heading_ids: set[str] = set()
            for block in self.body:
                if isinstance(block, HeadingBlock):
                    if block.id in heading_ids:
                        raise ValueError(f"duplicate heading id: {block.id}")
                    heading_ids.add(block.id)
        if self.slug and self.related_slugs and self.slug in self.related_slugs:
            raise ValueError("article cannot be related to itself")
        return self


class CategoryWriteRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    display_order: int = 0

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not SLUG_RE.fullmatch(value):
            raise ValueError("slug must contain lowercase letters, numbers and hyphens only")
        return value


class AuthorWriteRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    role: Optional[str] = Field(default=None, max_length=120)
    bio: Optional[str] = None
    avatar_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not SLUG_RE.fullmatch(value):
            raise ValueError("slug must contain lowercase letters, numbers and hyphens only")
        return value


class ArticleCategoryResponse(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None
    display_order: int = 0
    count: Optional[int] = None


class ArticleAuthorResponse(BaseModel):
    slug: str
    name: str
    role: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class RelatedArticleResponse(BaseModel):
    slug: str
    title: str
    excerpt: str
    category: str
    reading_minutes: int


class ArticleSeoResponse(BaseModel):
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    canonical_url: Optional[str] = None
    og_image_url: Optional[str] = None


class ArticleListItem(BaseModel):
    id: str
    slug: str
    title: str
    summary: str
    category: ArticleCategoryResponse
    author: ArticleAuthorResponse
    reading_minutes: int
    hero_icon: str
    hero_image_url: Optional[str] = None
    status: str
    published_at: Optional[datetime]
    updated_at: datetime


class ArticleListResponse(BaseModel):
    items: list[ArticleListItem]
    next_cursor: Optional[str]


class ArticleDetailResponse(ArticleListItem):
    tldr: str
    body: list[ContentBlock]
    toc: list[ArticleSection]
    audience: list[str]
    related: list[RelatedArticleResponse]
    seo: ArticleSeoResponse


class ArticleImageUploadResponse(BaseModel):
    filename: str
    stored_path: str
    hero_image_url: str


class CategoriesResponse(BaseModel):
    items: list[ArticleCategoryResponse]


class SitemapArticleItem(BaseModel):
    slug: str
    updated_at: datetime
    priority: float = 0.7
    changefreq: str = "monthly"


class SitemapArticlesResponse(BaseModel):
    items: list[SitemapArticleItem]
