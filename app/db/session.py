from collections.abc import Generator
from threading import Lock

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401

settings = get_settings()

# Keep the shared engine resilient in production:
# - pre_ping drops dead pooled connections before use
# - recycle avoids long-idle connections being reused behind proxies/load balancers
engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
_schema_compat_checked = False
_schema_compat_lock = Lock()


def ensure_runtime_schema_compatibility() -> None:
    # This keeps auth reads backward-compatible during partial rollouts where
    # the application code is deployed before the latest Alembic migration.
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            dialect_name = connection.dialect.name
            default_literal = "FALSE" if dialect_name == "postgresql" else "0"
            for table_name in (
                "app_download_content",
                "refresh_tokens",
                "phone_verification_codes",
                "password_reset_codes",
                "app_settings",
                "pending_registrations",
                "invited_account_tokens",
            ):
                if not inspector.has_table(table_name):
                    Base.metadata.tables[table_name].create(bind=connection, checkfirst=True)

            if not inspector.has_table("users"):
                return
            column_names = {column["name"] for column in inspector.get_columns("users")}
            if "must_change_password" not in column_names:
                connection.execute(
                    text(
                        f"ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT {default_literal}"
                    )
                )
            if "phone_number" not in column_names:
                connection.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(16) NULL"))
            if "is_phone_verified" not in column_names:
                connection.execute(
                    text(
                        f"ALTER TABLE users ADD COLUMN is_phone_verified BOOLEAN NOT NULL DEFAULT {default_literal}"
                    )
                )
                connection.execute(
                    text("UPDATE users SET is_phone_verified = CASE WHEN phone_number IS NOT NULL THEN 1 ELSE 0 END")
                )
    except SQLAlchemyError:
        # If schema introspection or the compat DDL fails, keep startup alive
        # and let the normal migration process handle it. Request-level errors
        # will surface the remaining issue more clearly than a boot loop.
        return


def ensure_runtime_schema_compatibility_once() -> None:
    global _schema_compat_checked
    if _schema_compat_checked:
        return
    with _schema_compat_lock:
        if _schema_compat_checked:
            return
        ensure_runtime_schema_compatibility()
        _schema_compat_checked = True


def get_db() -> Generator[Session, None, None]:
    ensure_runtime_schema_compatibility_once()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
