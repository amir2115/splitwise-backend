from app.admin.security import decode_admin_access_token
from app.models.user import User


def test_admin_login_and_me(client):
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    )

    assert login.status_code == 200
    payload = login.json()
    assert payload["admin"]["username"] == "panel_admin"
    assert payload["access_token"]

    decoded = decode_admin_access_token(payload["access_token"])
    assert decoded["type"] == "admin_access"

    me = client.get(
        "/api/v1/admin/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json() == {"username": "panel_admin"}


def test_admin_login_is_rate_limited_after_repeated_failures(client):
    for _ in range(5):
        response = client.post(
            "/api/v1/admin/auth/login",
            json={"username": "panel_admin", "password": "wrong-password"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "wrong-password"},
    )
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["error"]["code"] == "admin_rate_limited"


def test_admin_users_requires_authentication(client):
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 401


def test_admin_users_support_search_filters_sort_and_counts(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner User", "username": "owner_user", "password": "password123"},
    ).json()
    client.post(
        "/api/v1/auth/register",
        json={"name": "Alice Example", "username": "alice", "password": "password123"},
    )
    client.post(
        "/api/v1/auth/register",
        json={"name": "Bob Sample", "username": "bob", "password": "password123"},
    )

    created = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
        json={"name": "Needs Reset", "username": "needs_reset", "password": "12345678"},
    )
    assert created.status_code == 201

    group = client.post(
        "/api/v1/groups",
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
        json={"name": "Admin Metrics Group"},
    )
    assert group.status_code == 200

    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        params={
            "search": "e",
            "must_change_password": "true",
            "sort_by": "groups_count",
            "sort_order": "desc",
            "page": 1,
            "page_size": 10,
        },
    )

    assert users.status_code == 200
    payload = users.json()
    assert payload["summary"]["total_users"] == 1
    assert payload["summary"]["must_change_password_count"] == 1
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["username"] == "needs_reset"
    assert payload["items"][0]["groups_count"] == 0
    assert payload["items"][0]["active_refresh_tokens_count"] == 0


def test_admin_user_list_exposes_group_and_token_counts(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner User", "username": "owner_user", "password": "password123"},
    ).json()
    client.post(
        "/api/v1/groups",
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
        json={"name": "First Group"},
    )
    client.post(
        "/api/v1/groups",
        headers={"Authorization": f"Bearer {owner['tokens']['access_token']}"},
        json={"name": "Second Group"},
    )
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()

    users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        params={"search": "owner_user"},
    )

    assert users.status_code == 200
    payload = users.json()
    assert payload["items"][0]["username"] == "owner_user"
    assert payload["items"][0]["groups_count"] == 2
    assert payload["items"][0]["active_refresh_tokens_count"] == 1


def test_admin_user_list_exposes_phone_number(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner User", "username": "owner_user", "password": "password123"},
    ).json()
    access_token = owner["tokens"]["access_token"]

    request_code = client.post(
        "/api/v1/auth/phone/request-verification",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"phone_number": "09120000000"},
    )
    assert request_code.status_code == 200

    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()

    users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        params={"search": "owner_user"},
    )

    assert users.status_code == 200
    payload = users.json()
    assert payload["items"][0]["username"] == "owner_user"
    assert "phone_number" in payload["items"][0]


def test_admin_can_update_user_name_and_phone_number(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner User", "username": "owner_user", "password": "password123"},
    ).json()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()

    updated = client.patch(
        f"/api/v1/admin/users/{owner['user']['id']}",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"name": "Owner Updated", "phone_number": "09120000000"},
    )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["name"] == "Owner Updated"
    assert payload["phone_number"] == "989120000000"


def test_admin_can_clear_user_phone_number(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner User", "username": "owner_user", "password": "password123"},
    ).json()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()

    first_update = client.patch(
        f"/api/v1/admin/users/{owner['user']['id']}",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"phone_number": "09120000000"},
    )
    assert first_update.status_code == 200

    cleared = client.patch(
        f"/api/v1/admin/users/{owner['user']['id']}",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"phone_number": ""},
    )

    assert cleared.status_code == 200
    assert cleared.json()["phone_number"] is None


def test_admin_can_delete_user(client, db_session):
    owner = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner User", "username": "owner_user", "password": "password123"},
    ).json()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()

    deleted = client.delete(
        f"/api/v1/admin/users/{owner['user']['id']}",
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )

    assert deleted.status_code == 204
    assert db_session.get(User, owner["user"]["id"]) is None

    users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        params={"search": "owner_user"},
    )
    assert users.status_code == 200
    assert users.json()["pagination"]["total"] == 0


def test_admin_runtime_settings_cast_numeric_template_ids_to_strings(client):
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    updated = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={
            "sms_ir_verify_template_id": "664647",
            "sms_ir_invited_account_template_id": "975820",
            "sms_ir_verify_parameter_name": "OTP",
            "sms_ir_invited_account_link_parameter_name": "TOKEN",
            "sms_ir_invited_account_group_name_parameter_name": "GROUP_NAME",
            "web_app_base_url": "https://pwa.splitwise.ir",
        },
    )

    assert updated.status_code == 200

    response = client.get("/api/v1/admin/settings/runtime", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["sms_ir_verify_template_id"] == "664647"
    assert payload["sms_ir_invited_account_template_id"] == "975820"
