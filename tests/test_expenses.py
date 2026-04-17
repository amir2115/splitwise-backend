def test_equal_split_normalization(client, auth_headers, seeded_group):
    group = seeded_group["group"]
    alice, bob, carol = seeded_group["members"]

    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Taxi",
            "note": None,
            "total_amount": 100,
            "split_type": "EQUAL",
            "payers": [{"member_id": alice["id"], "amount": 100}],
            "shares": [
                {"member_id": carol["id"], "amount": 0},
                {"member_id": bob["id"], "amount": 0},
                {"member_id": alice["id"], "amount": 0},
            ],
        },
    )
    assert response.status_code == 201
    shares = {item["member_id"]: item["amount"] for item in response.json()["shares"]}
    expected_order = sorted([alice["id"], bob["id"], carol["id"]])
    assert shares[expected_order[0]] == 34
    assert shares[expected_order[1]] == 33
    assert shares[expected_order[2]] == 33


def test_exact_split_validation_failure(client, auth_headers, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Lunch",
            "note": None,
            "total_amount": 300,
            "split_type": "EXACT",
            "payers": [{"member_id": alice["id"], "amount": 300}],
            "shares": [{"member_id": alice["id"], "amount": 100}, {"member_id": bob["id"], "amount": 100}],
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_expense"


def test_expense_with_pending_invite_member_returns_actionable_error(client, seeded_users):
    owner = seeded_users["owner"]
    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    pending_member = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    ).json()["member"]

    response = client.post(
        "/api/v1/expenses",
        headers=owner["headers"],
        json={
            "group_id": group["id"],
            "title": "Dinner",
            "note": None,
            "total_amount": 100,
            "split_type": "EXACT",
            "payers": [{"member_id": pending_member["id"], "amount": 100}],
            "shares": [{"member_id": pending_member["id"], "amount": 100}],
        },
    )

    assert response.status_code == 400
    payload = response.json()["error"]
    assert payload["code"] == "pending_member_invite_acceptance_required"
    assert payload["details"]["pending_members"] == [{"member_id": pending_member["id"], "username": "alice"}]
    assert "alice" in payload["message"]
