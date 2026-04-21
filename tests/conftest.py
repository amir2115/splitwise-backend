from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.config import get_settings
from app.models.domain import UserConnection
from app.services.admin_service import admin_login_rate_limiter


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def register_user(client: TestClient, *, name: str, username: str, password: str = "password123") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": name, "username": username, "password": password},
    )
    assert response.status_code == 201
    payload = response.json()
    return {
        "user": payload["user"],
        "headers": {"Authorization": f"Bearer {payload['tokens']['access_token']}"},
    }


def connect_users(db_session: Session, *user_ids: str) -> None:
    owner_id = user_ids[0]
    for other_id in user_ids[1:]:
        low_id, high_id = sorted((owner_id, other_id))
        db_session.add(UserConnection(user_low_id=low_id, user_high_id=high_id))
    db_session.commit()


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    get_settings.cache_clear()
    admin_login_rate_limiter.reset()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def admin_settings(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("ADMIN_PANEL_USERNAME", "panel_admin")
    monkeypatch.setenv("ADMIN_PANEL_PASSWORD", "super-secret")
    monkeypatch.delenv("ADMIN_PANEL_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("ADMIN_PANEL_JWT_SECRET", "admin-test-secret")
    monkeypatch.setenv("ADMIN_PANEL_RATE_LIMIT_ATTEMPTS", "5")
    monkeypatch.setenv("ADMIN_PANEL_RATE_LIMIT_WINDOW_MINUTES", "10")
    monkeypatch.setenv("ADMIN_PANEL_RATE_LIMIT_LOCKOUT_MINUTES", "15")
    monkeypatch.setenv("SMS_IR_API_KEY", "test-sms-api-key")
    monkeypatch.setenv("SMS_IR_VERIFY_TEMPLATE_ID", "100000")
    monkeypatch.setenv("SMS_IR_VERIFY_PARAMETER_NAME", "Code")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
def owner_account(client: TestClient) -> dict:
    return register_user(client, name="Owner", username="owner")


@pytest.fixture
def auth_headers(owner_account: dict[str, dict]) -> dict[str, str]:
    return owner_account["headers"]


@pytest.fixture
def second_account(client: TestClient) -> dict:
    return register_user(client, name="Second User", username="second")


@pytest.fixture
def seeded_users(client: TestClient) -> dict:
    return {
        "owner": register_user(client, name="Owner", username="owner"),
        "alice": register_user(client, name="Alice", username="alice"),
        "bob": register_user(client, name="Bob", username="bob"),
        "carol": register_user(client, name="Carol", username="carol"),
    }


@pytest.fixture
def seeded_group(client: TestClient, db_session: Session, seeded_users: dict) -> dict:
    owner = seeded_users["owner"]
    alice_user = seeded_users["alice"]["user"]
    bob_user = seeded_users["bob"]["user"]
    carol_user = seeded_users["carol"]["user"]
    connect_users(db_session, owner["user"]["id"], alice_user["id"], bob_user["id"], carol_user["id"])

    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    alice = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    ).json()["member"]
    bob = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "bob", "is_archived": False},
    ).json()["member"]
    carol = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "carol", "is_archived": False},
    ).json()["member"]
    return {"group": group, "members": [alice, bob, carol], "users": seeded_users}
