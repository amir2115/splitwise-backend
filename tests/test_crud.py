def test_group_crud(client, auth_headers):
    created = client.post("/api/v1/groups", headers=auth_headers, json={"name": "Home"}).json()
    assert created["name"] == "Home"

    listing = client.get("/api/v1/groups", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    updated = client.patch(f"/api/v1/groups/{created['id']}", headers=auth_headers, json={"name": "Home 2"}).json()
    assert updated["name"] == "Home 2"

    deleted = client.delete(f"/api/v1/groups/{created['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/groups", headers=auth_headers).json() == []


def test_member_crud(client, auth_headers):
    group = client.post("/api/v1/groups", headers=auth_headers, json={"name": "Trip"}).json()
    created = client.post(
        "/api/v1/members",
        headers=auth_headers,
        json={"group_id": group["id"], "name": "Alice", "is_archived": False},
    ).json()
    assert created["name"] == "Alice"

    updated = client.patch(f"/api/v1/members/{created['id']}", headers=auth_headers, json={"is_archived": True}).json()
    assert updated["is_archived"] is True

    deleted = client.delete(f"/api/v1/members/{created['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/members?group_id={group['id']}", headers=auth_headers).json() == []


def test_expense_crud(client, auth_headers, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    created = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Dinner",
            "note": "Team dinner",
            "total_amount": 300,
            "split_type": "EXACT",
            "payers": [{"member_id": alice["id"], "amount": 300}],
            "shares": [{"member_id": alice["id"], "amount": 150}, {"member_id": bob["id"], "amount": 150}],
        },
    )
    assert created.status_code == 201
    expense = created.json()
    assert expense["title"] == "Dinner"

    updated = client.patch(
        f"/api/v1/expenses/{expense['id']}",
        headers=auth_headers,
        json={"title": "Dinner 2", "note": "Updated note"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Dinner 2"

    deleted = client.delete(f"/api/v1/expenses/{expense['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/expenses?group_id={group['id']}", headers=auth_headers).json() == []


def test_settlement_crud(client, auth_headers, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    created = client.post(
        "/api/v1/settlements",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "from_member_id": bob["id"],
            "to_member_id": alice["id"],
            "amount": 120,
            "note": "Payback",
        },
    )
    assert created.status_code == 201
    settlement = created.json()

    updated = client.patch(
        f"/api/v1/settlements/{settlement['id']}",
        headers=auth_headers,
        json={"amount": 150, "note": "Adjusted"},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 150

    deleted = client.delete(f"/api/v1/settlements/{settlement['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/settlements?group_id={group['id']}", headers=auth_headers).json() == []
