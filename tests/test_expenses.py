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
