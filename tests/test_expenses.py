def test_equal_split_normalization(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, carol = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

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


def test_exact_split_validation_failure(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]
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


def test_share_split_distributes_proportionally(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, carol = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Dinner",
            "note": None,
            "total_amount": 300,
            "split_type": "SHARE",
            "payers": [{"member_id": alice["id"], "amount": 300}],
            "shares": [
                {"member_id": alice["id"], "amount": 0, "weight": 1},
                {"member_id": bob["id"], "amount": 0, "weight": 1},
                {"member_id": carol["id"], "amount": 0, "weight": 1},
            ],
        },
    )
    assert response.status_code == 201
    shares = {item["member_id"]: item["amount"] for item in response.json()["shares"]}
    assert shares[alice["id"]] + shares[bob["id"]] + shares[carol["id"]] == 300
    assert all(amt == 100 for amt in shares.values())


def test_share_split_with_decimal_weights(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, carol = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Lunch",
            "note": None,
            "total_amount": 450000,
            "split_type": "SHARE",
            "payers": [{"member_id": alice["id"], "amount": 450000}],
            "shares": [
                {"member_id": alice["id"], "amount": 0, "weight": 2},
                {"member_id": bob["id"], "amount": 0, "weight": 1.5},
                {"member_id": carol["id"], "amount": 0, "weight": 0.5},
            ],
        },
    )
    assert response.status_code == 201
    shares = {item["member_id"]: item for item in response.json()["shares"]}
    # Total = 450000, total weight = 4, per-share = 112500
    # Alice: 2 * 112500 = 225000; Bob: 168750; Carol: 56250; total = 450000
    assert shares[alice["id"]]["amount"] == 225000
    assert shares[bob["id"]]["amount"] == 168750
    assert shares[carol["id"]]["amount"] == 56250
    assert shares[alice["id"]]["weight"] == 2
    assert shares[bob["id"]]["weight"] == 1.5
    assert shares[carol["id"]]["weight"] == 0.5
    total = sum(s["amount"] for s in shares.values())
    assert total == 450000


def test_share_split_zero_weight_skips_member(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, carol = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Coffee",
            "note": None,
            "total_amount": 200,
            "split_type": "SHARE",
            "payers": [{"member_id": alice["id"], "amount": 200}],
            "shares": [
                {"member_id": alice["id"], "amount": 0, "weight": 1},
                {"member_id": bob["id"], "amount": 0, "weight": 1},
                {"member_id": carol["id"], "amount": 0, "weight": 0},
            ],
        },
    )
    assert response.status_code == 201
    shares = {item["member_id"]: item["amount"] for item in response.json()["shares"]}
    assert shares[alice["id"]] == 100
    assert shares[bob["id"]] == 100
    assert shares[carol["id"]] == 0


def test_share_split_rejects_all_zero_weights(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Coffee",
            "note": None,
            "total_amount": 200,
            "split_type": "SHARE",
            "payers": [{"member_id": alice["id"], "amount": 200}],
            "shares": [
                {"member_id": alice["id"], "amount": 0, "weight": 0},
                {"member_id": bob["id"], "amount": 0, "weight": 0},
            ],
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_expense"


def test_share_split_rounding_leftover_goes_to_heaviest_weight(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, carol = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

    # total = 100, weights = [1, 1, 1]; perShare = 33.333..., rounded each = 33
    # Sum = 99; leftover = 1; goes to a share with max weight (first by argmax).
    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Taxi",
            "note": None,
            "total_amount": 100,
            "split_type": "SHARE",
            "payers": [{"member_id": alice["id"], "amount": 100}],
            "shares": [
                {"member_id": alice["id"], "amount": 0, "weight": 1},
                {"member_id": bob["id"], "amount": 0, "weight": 1},
                {"member_id": carol["id"], "amount": 0, "weight": 1},
            ],
        },
    )
    assert response.status_code == 201
    amounts = [s["amount"] for s in response.json()["shares"]]
    assert sum(amounts) == 100
    assert sorted(amounts) == [33, 33, 34]


def test_share_split_rounds_half_up_to_match_frontend(client, seeded_group):
    """Backend uses half-up rounding (math.floor(x + 0.5)) so client-side
    preview from Math.round matches what the server persists."""
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

    # total=5, weights=[1, 1]; perShare = 2.5; half-up rounds to 3 each.
    # Sum = 6; leftover = -1; subtracted from the first share with max weight.
    # Result: alice (first max) = 3 - 1 = 2; bob = 3
    response = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Half-up",
            "note": None,
            "total_amount": 5,
            "split_type": "SHARE",
            "payers": [{"member_id": alice["id"], "amount": 5}],
            "shares": [
                {"member_id": alice["id"], "amount": 0, "weight": 1},
                {"member_id": bob["id"], "amount": 0, "weight": 1},
            ],
        },
    )
    assert response.status_code == 201
    shares = {item["member_id"]: item["amount"] for item in response.json()["shares"]}
    assert sum(shares.values()) == 5
    # Half-up: each rounds to 3, sum=6, leftover=-1 → alice (first max) absorbs it
    assert shares[alice["id"]] == 2
    assert shares[bob["id"]] == 3
