from app.admin.security import decode_admin_access_token
from app.models.domain import AppSetting
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
    assert blocked.json()["error"]["code"] == "admin_rate_limited"


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
    assert group.status_code == 201

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


def test_admin_user_list_exposes_phone_number(client, db_session):
    db_session.add(AppSetting(key="sms_otp_bypass_enabled", value="true"))
    db_session.commit()
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


def test_admin_users_support_phone_contains_search(client):
    with_phone = client.post(
        "/api/v1/auth/register",
        json={"name": "Phone Owner", "username": "phone_owner", "password": "password123"},
    ).json()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()

    updated = client.patch(
        f"/api/v1/admin/users/{with_phone['user']['id']}",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        json={"phone_number": "09120000000", "is_phone_verified": True},
    )
    assert updated.status_code == 200

    users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {login['access_token']}"},
        params={"search": "0912"},
    )

    assert users.status_code == 200
    payload = users.json()
    assert payload["pagination"]["total"] == 1
    assert payload["items"][0]["username"] == "phone_owner"


def test_admin_users_support_phone_sorts(client):
    no_phone = client.post(
        "/api/v1/auth/register",
        json={"name": "No Phone", "username": "no_phone", "password": "password123"},
    ).json()
    with_unverified_phone = client.post(
        "/api/v1/auth/register",
        json={"name": "Unverified Phone", "username": "unverified_phone", "password": "password123"},
    ).json()
    with_verified_phone = client.post(
        "/api/v1/auth/register",
        json={"name": "Verified Phone", "username": "verified_phone", "password": "password123"},
    ).json()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    unverified_update = client.patch(
        f"/api/v1/admin/users/{with_unverified_phone['user']['id']}",
        headers=headers,
        json={"phone_number": "09120000001", "is_phone_verified": False},
    )
    assert unverified_update.status_code == 200

    verified_update = client.patch(
        f"/api/v1/admin/users/{with_verified_phone['user']['id']}",
        headers=headers,
        json={"phone_number": "09120000002", "is_phone_verified": True},
    )
    assert verified_update.status_code == 200

    has_phone_sorted = client.get(
        "/api/v1/admin/users",
        headers=headers,
        params={"sort_by": "has_phone_number", "sort_order": "desc", "page_size": 10},
    )
    assert has_phone_sorted.status_code == 200
    has_phone_usernames = [item["username"] for item in has_phone_sorted.json()["items"]]
    assert has_phone_usernames.index("unverified_phone") < has_phone_usernames.index("no_phone")
    assert has_phone_usernames.index("verified_phone") < has_phone_usernames.index("no_phone")

    verified_sorted = client.get(
        "/api/v1/admin/users",
        headers=headers,
        params={"sort_by": "is_phone_verified", "sort_order": "desc", "page_size": 10},
    )
    assert verified_sorted.status_code == 200
    verified_usernames = [item["username"] for item in verified_sorted.json()["items"]]
    assert verified_usernames.index("verified_phone") < verified_usernames.index("unverified_phone")
    assert verified_usernames.index("verified_phone") < verified_usernames.index("no_phone")


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
    assert payload["is_phone_verified"] is False


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


def test_admin_can_update_phone_verification_status(client):
    owner = client.post(
        "/api/v1/auth/register",
        json={"name": "Owner User", "username": "owner_user", "password": "password123"},
    ).json()
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    first_update = client.patch(
        f"/api/v1/admin/users/{owner['user']['id']}",
        headers=headers,
        json={"phone_number": "09120000000", "is_phone_verified": False},
    )
    assert first_update.status_code == 200
    assert first_update.json()["is_phone_verified"] is False

    verified = client.patch(
        f"/api/v1/admin/users/{owner['user']['id']}",
        headers=headers,
        json={"is_phone_verified": True},
    )

    assert verified.status_code == 200
    assert verified.json()["is_phone_verified"] is True


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
            "phone_verification_required": True,
            "sms_ir_verify_template_id": "664647",
            "sms_ir_verify_template_id_android": "775758",
            "sms_ir_invited_account_template_id": "975820",
            "sms_ir_verify_parameter_name": "OTP",
            "sms_otp_bypass_enabled": True,
            "sms_ir_invited_account_link_parameter_name": "TOKEN",
            "sms_ir_invited_account_group_name_parameter_name": "GROUP_NAME",
            "web_app_base_url": "https://pwa.splitwise.ir",
        },
    )

    assert updated.status_code == 200

    response = client.get("/api/v1/admin/settings/runtime", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["phone_verification_required"] is True
    assert payload["sms_ir_verify_template_id"] == "664647"
    assert payload["sms_ir_verify_template_id_android"] == "775758"
    assert payload["sms_ir_invited_account_template_id"] == "975820"
    assert payload["sms_otp_bypass_enabled"] is True


def test_admin_runtime_settings_can_disable_sms_otp_bypass(client):
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    enabled = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={"sms_otp_bypass_enabled": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["sms_otp_bypass_enabled"] is True

    disabled = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={"sms_otp_bypass_enabled": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["sms_otp_bypass_enabled"] is False


def test_admin_runtime_settings_can_toggle_phone_verification_required(client):
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    enabled = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={"phone_verification_required": True},
    )
    assert enabled.status_code == 200
    assert enabled.json()["phone_verification_required"] is True

    disabled = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={"phone_verification_required": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["phone_verification_required"] is False


def test_admin_runtime_settings_can_manage_public_site_settings(client):
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    updated = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={
            "support_email": "hello@splitwise.ir",
            "support_url": "mailto:hello@splitwise.ir",
            "twitter_url": "https://x.com/dongino",
            "instagram_url": "",
            "telegram_url": "https://t.me/dongino",
            "linkedin_url": None,
            "enamad_url": "https://trustseal.enamad.ir/example",
            "pwa_url": "https://pwa.splitwise.ir",
            "bazaar_url": "https://cafebazaar.ir/app/com.encer.offlinesplitwise",
            "myket_url": "https://myket.ir/app/com.encer.offlinesplitwise",
            "apk_url": "https://splitwise.ir/files/app.apk",
            "footer_short_text": "متن فوتر تست",
            "contact_body": "متن تماس تست",
        },
    )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["support_email"] == "hello@splitwise.ir"
    assert payload["twitter_url"] == "https://x.com/dongino"
    assert payload["instagram_url"] is None
    assert payload["telegram_url"] == "https://t.me/dongino"
    assert payload["footer_short_text"] == "متن فوتر تست"


def test_public_site_settings_exposes_only_public_values(client):
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    response = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={
            "sms_ir_api_key": "secret-sms-key",
            "twitter_url": "https://x.com/dongino",
            "support_email": "support@splitwise.ir",
        },
    )
    assert response.status_code == 200

    public = client.get("/api/v1/site-settings")

    assert public.status_code == 200
    payload = public.json()
    assert payload["twitter_url"] == "https://x.com/dongino"
    assert payload["support_email"] == "support@splitwise.ir"
    assert "sms_ir_api_key" not in payload
    assert "sms_ir_api_key_masked" not in payload


def test_admin_runtime_settings_patch_preserves_unsent_fields(client):
    login = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    first = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={"support_email": "hello@splitwise.ir", "twitter_url": "https://x.com/dongino"},
    )
    assert first.status_code == 200

    second = client.patch(
        "/api/v1/admin/settings/runtime",
        headers=headers,
        json={"support_email": "support@splitwise.ir"},
    )

    assert second.status_code == 200
    payload = second.json()
    assert payload["support_email"] == "support@splitwise.ir"
    assert payload["twitter_url"] == "https://x.com/dongino"
