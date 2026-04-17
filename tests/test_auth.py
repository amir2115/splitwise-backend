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
    assert me.json()["must_change_password"] is False


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
