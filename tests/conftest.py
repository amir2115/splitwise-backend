from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner", "username": "owner", "password": "password123"},
    )
    token = response.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_group(client: TestClient, auth_headers: dict[str, str]) -> dict:
    group = client.post("/api/v1/groups", headers=auth_headers, json={"name": "Trip"}).json()
    alice = client.post(
        "/api/v1/members",
        headers=auth_headers,
        json={"group_id": group["id"], "name": "Alice", "is_archived": False},
    ).json()
    bob = client.post(
        "/api/v1/members",
        headers=auth_headers,
        json={"group_id": group["id"], "name": "Bob", "is_archived": False},
    ).json()
    carol = client.post(
        "/api/v1/members",
        headers=auth_headers,
        json={"group_id": group["id"], "name": "Carol", "is_archived": False},
    ).json()
    return {"group": group, "members": [alice, bob, carol]}
