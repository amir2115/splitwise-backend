"""add articles content tables

Revision ID: 20260430_000012
Revises: 20260421_000011
Create Date: 2026-04-30 00:00:12.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260430_000012"
down_revision = "20260421_000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    article_status = sa.Enum("draft", "published", "archived", name="article_status")

    op.create_table(
        "article_categories",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_article_categories_slug"),
    )
    op.create_index(op.f("ix_article_categories_slug"), "article_categories", ["slug"], unique=False)

    op.create_table(
        "article_authors",
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=120), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_article_authors_slug"),
    )
    op.create_index(op.f("ix_article_authors_slug"), "article_authors", ["slug"], unique=False)

    op.create_table(
        "articles",
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("tldr", sa.Text(), nullable=False),
        sa.Column("hero_icon", sa.String(length=16), server_default="✦", nullable=False),
        sa.Column("reading_minutes", sa.Integer(), server_default="5", nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=36), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("toc", sa.JSON(), nullable=False),
        sa.Column("audience", sa.JSON(), nullable=False),
        sa.Column("related_slugs", sa.JSON(), nullable=False),
        sa.Column("meta_title", sa.String(length=220), nullable=True),
        sa.Column("meta_description", sa.String(length=320), nullable=True),
        sa.Column("og_image_url", sa.String(length=500), nullable=True),
        sa.Column("canonical_url", sa.String(length=500), nullable=True),
        sa.Column("status", article_status, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["article_authors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["article_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_articles_slug"),
    )
    op.create_index("idx_articles_status_pub", "articles", ["status", "published_at"], unique=False)
    op.create_index(op.f("ix_articles_author_id"), "articles", ["author_id"], unique=False)
    op.create_index(op.f("ix_articles_category_id"), "articles", ["category_id"], unique=False)
    op.create_index(op.f("ix_articles_slug"), "articles", ["slug"], unique=False)

    op.create_table(
        "article_redirects",
        sa.Column("from_slug", sa.String(length=120), nullable=False),
        sa.Column("to_slug", sa.String(length=120), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["to_slug"], ["articles.slug"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("from_slug", name="uq_article_redirects_from_slug"),
    )


def downgrade() -> None:
    op.drop_table("article_redirects")
    op.drop_index(op.f("ix_articles_slug"), table_name="articles")
    op.drop_index(op.f("ix_articles_category_id"), table_name="articles")
    op.drop_index(op.f("ix_articles_author_id"), table_name="articles")
    op.drop_index("idx_articles_status_pub", table_name="articles")
    op.drop_table("articles")
    op.drop_index(op.f("ix_article_authors_slug"), table_name="article_authors")
    op.drop_table("article_authors")
    op.drop_index(op.f("ix_article_categories_slug"), table_name="article_categories")
    op.drop_table("article_categories")
    sa.Enum(name="article_status").drop(op.get_bind(), checkfirst=True)
