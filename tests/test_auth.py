from datetime import timedelta

from app.auth.security import hash_password, verify_password
from app.core.config import get_settings
from app.core.time import utcnow
from app.models.user import InvitedAccountToken, PasswordResetCode, PendingRegistration, PhoneVerificationCode, User


class _FakeSmsResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise AssertionError("Unexpected HTTP error in fake SMS response")

    def json(self) -> dict:
        return self._payload


def test_register_login_refresh_and_me(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"name": "Amir Test", "username": "amir_test", "password": "password123"},
    )
    assert register.status_code == 201
    tokens = register.json()["tokens"]

    login = client.post("/api/v1/auth/login", json={"username": "amir_test", "password": "password123"})
    assert login.status_code == 200

    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]
    assert refresh.json()["refresh_token"] != tokens["refresh_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login.json()['tokens']['access_token']}"})
    assert me.status_code == 200
    assert me.json()["name"] == "Amir Test"
    assert me.json()["username"] == "amir_test"
    assert me.json()["phone_number"] is None
    assert me.json()["must_change_password"] is False


def test_register_request_and_verify_creates_verified_user_and_tokens(client, db_session, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 123, "cost": 1.0}})

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)

    requested = client.post(
        "/api/v1/auth/register/request",
        json={
            "name": "Register User",
            "username": "register_user",
            "password": "password123",
            "phone_number": "09120000000",
        },
    )

    assert requested.status_code == 200
    request_payload = requested.json()
    assert request_payload["phone_number"] == "989120000000"
    assert request_payload["message_id"] == 123

    pending_record = db_session.query(PendingRegistration).one()
    sent_code = captured["json"]["parameters"][0]["value"]
    assert pending_record.username == "register_user"
    assert pending_record.phone_number == "989120000000"
    assert pending_record.password_hash != "password123"
    assert pending_record.code_hash != sent_code
    assert verify_password(sent_code, pending_record.code_hash)

    verified = client.post(
        "/api/v1/auth/register/verify",
        json={"registration_id": request_payload["registration_id"], "code": sent_code},
    )

    assert verified.status_code == 200
    verify_payload = verified.json()
    assert verify_payload["user"]["username"] == "register_user"
    assert verify_payload["user"]["phone_number"] == "989120000000"
    assert verify_payload["user"]["is_phone_verified"] is True
    assert verify_payload["tokens"]["access_token"]
    assert verify_payload["tokens"]["refresh_token"]

    user = db_session.query(User).filter(User.username == "register_user").one()
    assert user.phone_number == "989120000000"
    assert user.is_phone_verified is True

    db_session.refresh(pending_record)
    assert pending_record.consumed_at is not None


def test_invited_account_completes_without_pre_verifying_phone(client, db_session):
    user = User(
        name="Invited User",
        username="invited_user",
        phone_number="989120000000",
        is_phone_verified=False,
        password_hash=hash_password("12345678"),
        must_change_password=True,
    )
    db_session.add(user)
    db_session.flush()

    token_record = InvitedAccountToken(
        user_id=user.id,
        token_jti="short-invite-token",
        expires_at=utcnow() + timedelta(hours=1),
        last_sent_at=utcnow(),
        send_attempts=1,
    )
    db_session.add(token_record)
    db_session.commit()

    requested = client.post("/api/v1/auth/invited-account/request", json={"token": "short-invite-token"})
    assert requested.status_code == 200
    assert requested.json()["requires_phone_verification"] is False
    assert requested.json()["masked_phone_number"] == "98912***000"

    completed = client.post(
        "/api/v1/auth/invited-account/complete",
        json={"token": "short-invite-token", "new_password": "password123"},
    )

    assert completed.status_code == 200
    payload = completed.json()
    assert payload["user"]["username"] == "invited_user"
    assert payload["user"]["is_phone_verified"] is False
    assert payload["user"]["must_change_password"] is False
    assert payload["tokens"]["access_token"]
    assert payload["tokens"]["refresh_token"]

    db_session.refresh(user)
    db_session.refresh(token_record)
    assert verify_password("password123", user.password_hash)
    assert user.is_phone_verified is False
    assert user.must_change_password is False
    assert token_record.consumed_at is not None


def test_inviter_can_create_user_with_forced_password_change(client, auth_headers):
    created = client.post(
        "/api/v1/auth/users",
        headers=auth_headers,
        json={"name": "New User", "username": "new_user", "password": "12345678"},
    )

    assert created.status_code == 201
    assert created.json()["username"] == "new_user"
    assert created.json()["must_change_password"] is True

    login = client.post("/api/v1/auth/login", json={"username": "new_user", "password": "12345678"})
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True


def test_change_password_clears_force_change_flag(client, auth_headers):
    created = client.post(
        "/api/v1/auth/users",
        headers=auth_headers,
        json={"name": "Needs Reset", "username": "needs_reset", "password": "12345678"},
    )
    login = client.post("/api/v1/auth/login", json={"username": "needs_reset", "password": "12345678"})
    access_token = login.json()["tokens"]["access_token"]

    changed = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current_password": "12345678", "new_password": "password123"},
    )

    assert created.status_code == 201
    assert changed.status_code == 200
    assert changed.json()["must_change_password"] is False

    relogin = client.post("/api/v1/auth/login", json={"username": "needs_reset", "password": "password123"})
    assert relogin.status_code == 200
    assert relogin.json()["user"]["must_change_password"] is False


def test_request_phone_verification_sends_sms_and_hashes_code(client, auth_headers, db_session, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 89545112, "cost": 1.0}})

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)

    response = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_number"] == "989120000000"
    assert payload["expires_in_seconds"] == 120
    assert payload["resend_available_in_seconds"] == 60
    assert payload["message_id"] == 89545112

    assert captured["url"] == "https://api.sms.ir/v1/send/verify"
    assert captured["headers"]["x-api-key"] == "test-sms-api-key"
    assert captured["json"]["templateId"] == 100000
    assert captured["json"]["mobile"] == "989120000000"
    assert captured["json"]["parameters"] == [{"name": "Code", "value": captured["json"]["parameters"][0]["value"]}]

    record = db_session.query(PhoneVerificationCode).one()
    sent_code = captured["json"]["parameters"][0]["value"]
    assert record.phone_number == "989120000000"
    assert record.code_hash != sent_code
    assert verify_password(sent_code, record.code_hash)


def test_request_phone_verification_requires_configuration(client, auth_headers, monkeypatch):
    monkeypatch.delenv("SMS_IR_API_KEY", raising=False)
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "phone_verification_not_configured"


def test_request_phone_verification_rejects_invalid_phone_number(client, auth_headers):
    response = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "02112345678"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_phone_number"


def test_request_phone_verification_rejects_phone_number_used_by_other_user(client, auth_headers, second_account, db_session, monkeypatch):
    other_user = db_session.get(User, second_account["user"]["id"])
    other_user.phone_number = "989120000000"
    db_session.commit()

    monkeypatch.setattr(
        "app.services.sms_service.httpx.post",
        lambda url, json, headers, timeout: _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 1, "cost": 1.0}}),
    )

    response = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "phone_number_taken"


def test_request_phone_verification_is_rate_limited(client, auth_headers, monkeypatch):
    monkeypatch.setattr(
        "app.services.sms_service.httpx.post",
        lambda url, json, headers, timeout: _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 1, "cost": 1.0}}),
    )

    first = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )
    second = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "phone_verification_rate_limited"


def test_verify_phone_number_sets_user_phone_number(client, auth_headers, db_session, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["code"] = json["parameters"][0]["value"]
        return _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 9, "cost": 1.0}})

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)

    requested = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "+989120000000"},
    )
    assert requested.status_code == 200

    verified = client.post(
        "/api/v1/auth/phone/verify",
        headers=auth_headers,
        json={"phone_number": "09120000000", "code": captured["code"]},
    )

    assert verified.status_code == 200
    assert verified.json()["phone_number"] == "989120000000"

    record = db_session.query(PhoneVerificationCode).one()
    assert record.consumed_at is not None


def test_verify_phone_number_rejects_invalid_code(client, auth_headers, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.sms_service.httpx.post",
        lambda url, json, headers, timeout: _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 9, "cost": 1.0}}),
    )

    requested = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )
    assert requested.status_code == 200

    verified = client.post(
        "/api/v1/auth/phone/verify",
        headers=auth_headers,
        json={"phone_number": "09120000000", "code": "00000"},
    )

    assert verified.status_code == 400
    assert verified.json()["error"]["code"] == "phone_verification_code_invalid"

    record = db_session.query(PhoneVerificationCode).one()
    assert record.verify_attempts == 1


def test_verify_phone_number_rejects_expired_code(client, auth_headers, db_session, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["code"] = json["parameters"][0]["value"]
        return _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 9, "cost": 1.0}})

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)

    requested = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )
    assert requested.status_code == 200

    record = db_session.query(PhoneVerificationCode).one()
    record.expires_at = utcnow()
    db_session.commit()

    verified = client.post(
        "/api/v1/auth/phone/verify",
        headers=auth_headers,
        json={"phone_number": "09120000000", "code": captured["code"]},
    )

    assert verified.status_code == 400
    assert verified.json()["error"]["code"] == "phone_verification_code_expired"


def test_verify_phone_number_cannot_reuse_consumed_code(client, auth_headers, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["code"] = json["parameters"][0]["value"]
        return _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 9, "cost": 1.0}})

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)

    requested = client.post(
        "/api/v1/auth/phone/request-verification",
        headers=auth_headers,
        json={"phone_number": "09120000000"},
    )
    assert requested.status_code == 200

    first_verify = client.post(
        "/api/v1/auth/phone/verify",
        headers=auth_headers,
        json={"phone_number": "09120000000", "code": captured["code"]},
    )
    second_verify = client.post(
        "/api/v1/auth/phone/verify",
        headers=auth_headers,
        json={"phone_number": "09120000000", "code": captured["code"]},
    )

    assert first_verify.status_code == 200
    assert second_verify.status_code == 404
    assert second_verify.json()["error"]["code"] == "phone_verification_code_not_found"


def test_request_password_reset_works_with_username_and_masks_phone(client, db_session, monkeypatch):
    captured = {}
    register = client.post(
        "/api/v1/auth/register",
        json={"name": "Reset User", "username": "reset_user", "password": "password123"},
    )
    user = db_session.get(User, register.json()["user"]["id"])
    user.phone_number = "989120000000"
    db_session.commit()

    def fake_post(url, json, headers, timeout):
        captured["code"] = json["parameters"][0]["value"]
        return _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 77, "cost": 1.0}})

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)

    response = client.post("/api/v1/auth/forgot-password/request", json={"identifier": "reset_user"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["masked_phone_number"] == "98912***000"
    assert payload["message_id"] == 77

    record = db_session.query(PasswordResetCode).one()
    assert verify_password(captured["code"], record.code_hash)


def test_request_password_reset_rejects_unknown_account(client):
    response = client.post("/api/v1/auth/forgot-password/request", json={"identifier": "missing_user"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "reset_account_not_found"


def test_request_password_reset_accepts_username_with_at_prefix(client, db_session, monkeypatch):
    register = client.post(
        "/api/v1/auth/register",
        json={"name": "Reset User", "username": "amir2115", "password": "password123"},
    )
    user = db_session.get(User, register.json()["user"]["id"])
    user.phone_number = "989120000000"
    db_session.commit()

    monkeypatch.setattr(
        "app.services.sms_service.httpx.post",
        lambda url, json, headers, timeout: _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 78, "cost": 1.0}}),
    )

    response = client.post("/api/v1/auth/forgot-password/request", json={"identifier": "@amir2115"})

    assert response.status_code == 200
    assert response.json()["masked_phone_number"] == "98912***000"


def test_request_password_reset_requires_registered_phone(client):
    client.post(
        "/api/v1/auth/register",
        json={"name": "Reset User", "username": "reset_user", "password": "password123"},
    )

    response = client.post("/api/v1/auth/forgot-password/request", json={"identifier": "reset_user"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "password_reset_phone_missing"


def test_verify_and_confirm_password_reset_returns_auth_response(client, db_session, monkeypatch):
    captured = {}
    register = client.post(
        "/api/v1/auth/register",
        json={"name": "Reset User", "username": "reset_user", "password": "password123"},
    )
    user = db_session.get(User, register.json()["user"]["id"])
    user.phone_number = "989120000000"
    db_session.commit()

    def fake_post(url, json, headers, timeout):
        captured["code"] = json["parameters"][0]["value"]
        return _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 55, "cost": 1.0}})

    monkeypatch.setattr("app.services.sms_service.httpx.post", fake_post)

    requested = client.post("/api/v1/auth/forgot-password/request", json={"identifier": "09120000000"})
    assert requested.status_code == 200

    verified = client.post(
        "/api/v1/auth/forgot-password/verify",
        json={"identifier": "reset_user", "code": captured["code"]},
    )
    assert verified.status_code == 200
    reset_token = verified.json()["reset_token"]

    confirmed = client.post(
        "/api/v1/auth/forgot-password/confirm",
        json={"reset_token": reset_token, "new_password": "new-password123"},
    )

    assert confirmed.status_code == 200
    payload = confirmed.json()
    assert payload["user"]["username"] == "reset_user"
    assert payload["tokens"]["access_token"]

    relogin = client.post("/api/v1/auth/login", json={"username": "reset_user", "password": "new-password123"})
    assert relogin.status_code == 200


def test_verify_password_reset_rejects_invalid_code(client, db_session, monkeypatch):
    register = client.post(
        "/api/v1/auth/register",
        json={"name": "Reset User", "username": "reset_user", "password": "password123"},
    )
    user = db_session.get(User, register.json()["user"]["id"])
    user.phone_number = "989120000000"
    db_session.commit()

    monkeypatch.setattr(
        "app.services.sms_service.httpx.post",
        lambda url, json, headers, timeout: _FakeSmsResponse({"status": 1, "message": "موفق", "data": {"messageId": 9, "cost": 1.0}}),
    )

    requested = client.post("/api/v1/auth/forgot-password/request", json={"identifier": "reset_user"})
    assert requested.status_code == 200

    verified = client.post(
        "/api/v1/auth/forgot-password/verify",
        json={"identifier": "reset_user", "code": "00000"},
    )

    assert verified.status_code == 400
    assert verified.json()["error"]["code"] == "password_reset_code_invalid"


def test_confirm_password_reset_rejects_invalid_token(client):
    confirmed = client.post(
        "/api/v1/auth/forgot-password/confirm",
        json={"reset_token": "invalid-token", "new_password": "new-password123"},
    )

    assert confirmed.status_code == 401
    assert confirmed.json()["error"]["code"] == "password_reset_token_invalid"
