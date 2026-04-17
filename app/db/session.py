from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

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


def ensure_runtime_schema_compatibility() -> None:
    # This keeps auth reads backward-compatible during partial rollouts where
    # the application code is deployed before the latest Alembic migration.
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            if not inspector.has_table("users"):
                return
            column_names = {column["name"] for column in inspector.get_columns("users")}
            if "must_change_password" in column_names:
                return

            dialect_name = connection.dialect.name
            default_literal = "FALSE" if dialect_name == "postgresql" else "0"
            connection.execute(
                text(
                    f"ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT {default_literal}"
                )
            )
    except SQLAlchemyError:
        # If schema introspection or the compat DDL fails, keep startup alive
        # and let the normal migration process handle it. Request-level errors
        # will surface the remaining issue more clearly than a boot loop.
        return


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
