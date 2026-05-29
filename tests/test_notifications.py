from app.models.user import FcmDeviceToken
from app.core.time import utcnow
from app.schemas.notifications import AdminNotificationSendRequest, NotificationTargetType
from app.services.notification_service import send_admin_notification


class FakeSender:
    def __init__(self, *, invalid_tokens=None):
        self.calls = []
        self.invalid_tokens = invalid_tokens or []

    def send(self, *, tokens, title, body, data):
        self.calls.append({"tokens": tokens, "title": title, "body": body, "data": data})
        return len(tokens) - len(self.invalid_tokens), self.invalid_tokens


def test_register_fcm_token_upserts_by_user_and_device(client, auth_headers, db_session):
    first = client.put(
        "/api/v1/notifications/fcm-token",
        headers=auth_headers,
        json={
            "token": "token-one",
            "device_id": "device-1",
            "platform": "android",
            "store_channel": "bazaar",
            "app_version_name": "1.0",
            "app_version_code": 1,
        },
    )
    second = client.put(
        "/api/v1/notifications/fcm-token",
        headers=auth_headers,
        json={
            "token": "token-two",
            "device_id": "device-1",
            "platform": "android",
            "store_channel": "bazaar",
            "app_version_name": "1.1",
            "app_version_code": 2,
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    records = db_session.query(FcmDeviceToken).all()
    assert len(records) == 1
    assert records[0].token == "token-two"
    assert records[0].is_active is True
    assert records[0].app_version_code == 2


def test_delete_fcm_token_deactivates_current_users_token(client, auth_headers, db_session):
    client.put(
        "/api/v1/notifications/fcm-token",
        headers=auth_headers,
        json={"token": "token-one", "device_id": "device-1"},
    )

    response = client.request(
        "DELETE",
        "/api/v1/notifications/fcm-token",
        headers=auth_headers,
        json={"device_id": "device-1"},
    )

    assert response.status_code == 204
    assert db_session.query(FcmDeviceToken).one().is_active is False


def test_admin_send_notification_requires_authentication(client):
    response = client.post(
        "/api/v1/admin/notifications/send",
        json={"target_type": "all", "title": "Hello", "body": "Body"},
    )

    assert response.status_code == 401


def test_admin_send_notification_missing_firebase_credentials_returns_503(client, auth_headers):
    client.put(
        "/api/v1/notifications/fcm-token",
        headers=auth_headers,
        json={"token": "token-one", "device_id": "device-1"},
    )
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()

    response = client.post(
        "/api/v1/admin/notifications/send",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"target_type": "all", "title": "Hello", "body": "Body"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "firebase_not_configured"


def test_send_admin_notification_targets_all_and_deactivates_invalid_tokens(db_session, seeded_users):
    owner = seeded_users["owner"]["user"]
    alice = seeded_users["alice"]["user"]
    db_session.add_all(
        [
            FcmDeviceToken(user_id=owner["id"], device_id="owner-device", token="owner-token", platform="android", is_active=True, last_seen_at=utcnow()),
            FcmDeviceToken(user_id=alice["id"], device_id="alice-device", token="alice-token", platform="android", is_active=True, last_seen_at=utcnow()),
        ]
    )
    db_session.commit()
    sender = FakeSender(invalid_tokens=["alice-token"])

    result = send_admin_notification(
        db_session,
        AdminNotificationSendRequest(target_type=NotificationTargetType.ALL, title="Hello", body="Body", data={"kind": "test"}),
        sender=sender,
    )

    assert result.attempted == 2
    assert result.sent == 1
    assert result.failed == 1
    assert set(sender.calls[0]["tokens"]) == {"owner-token", "alice-token"}
    assert db_session.query(FcmDeviceToken).filter_by(token="alice-token").one().is_active is False


def test_send_admin_notification_targets_specific_users(db_session, seeded_users):
    owner = seeded_users["owner"]["user"]
    alice = seeded_users["alice"]["user"]
    db_session.add_all(
        [
            FcmDeviceToken(user_id=owner["id"], device_id="owner-device", token="owner-token", platform="android", is_active=True, last_seen_at=utcnow()),
            FcmDeviceToken(user_id=alice["id"], device_id="alice-device", token="alice-token", platform="android", is_active=True, last_seen_at=utcnow()),
        ]
    )
    db_session.commit()
    sender = FakeSender()

    result = send_admin_notification(
        db_session,
        AdminNotificationSendRequest(
            target_type=NotificationTargetType.USER_IDS,
            user_ids=[alice["id"]],
            title="Hello",
            body="Body",
        ),
        sender=sender,
    )

    assert result.attempted == 1
    assert result.sent == 1
    assert result.failed == 0
    assert sender.calls[0]["tokens"] == ["alice-token"]
