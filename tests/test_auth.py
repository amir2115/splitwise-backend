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
