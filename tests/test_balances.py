def test_balance_calculation_behavior(client, auth_headers, seeded_group):
    group = seeded_group["group"]
    alice, bob, carol = seeded_group["members"]

    client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Hotel",
            "note": None,
            "total_amount": 900,
            "split_type": "EXACT",
            "payers": [{"member_id": alice["id"], "amount": 900}],
            "shares": [
                {"member_id": alice["id"], "amount": 300},
                {"member_id": bob["id"], "amount": 300},
                {"member_id": carol["id"], "amount": 300},
            ],
        },
    )
    client.post(
        "/api/v1/settlements",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "from_member_id": bob["id"],
            "to_member_id": alice["id"],
            "amount": 200,
            "note": "Partial settle",
        },
    )

    response = client.get(f"/api/v1/groups/{group['id']}/balances", headers=auth_headers)
    assert response.status_code == 200
    balances = {item["member_name"]: item for item in response.json()["balances"]}

    assert balances["Alice"]["paid_total"] == 900
    assert balances["Alice"]["owed_total"] == 500
    assert balances["Alice"]["net_balance"] == 400

    assert balances["Bob"]["paid_total"] == 200
    assert balances["Bob"]["owed_total"] == 300
    assert balances["Bob"]["net_balance"] == -100

    assert balances["Carol"]["net_balance"] == -300

    simplified = response.json()["simplified_debts"]
    assert simplified == [
        {"from_member_id": bob["id"], "to_member_id": alice["id"], "amount": 100},
        {"from_member_id": carol["id"], "to_member_id": alice["id"], "amount": 300},
    ]
