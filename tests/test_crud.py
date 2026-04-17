from app.models.domain import GroupInvite, GroupInviteStatus, GroupCard, MembershipStatus, UserConnection


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


def test_member_add_unknown_username_returns_error(client, auth_headers):
    group = client.post("/api/v1/groups", headers=auth_headers, json={"name": "Trip"}).json()
    created = client.post(
        "/api/v1/members",
        headers=auth_headers,
        json={"group_id": group["id"], "username": "missing_user", "is_archived": False},
    )
    assert created.status_code == 400
    assert created.json()["error"]["code"] == "username_not_found"


def test_inline_member_create_adds_user_without_invite_and_shows_both_members(client, seeded_users):
    owner = seeded_users["owner"]
    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()

    created = client.post(
        "/api/v1/members/inline-create",
        headers=owner["headers"],
        json={
            "group_id": group["id"],
            "name": "Inline User",
            "username": "inline_user",
            "password": "12345678",
            "is_archived": False,
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["outcome"] == "added"
    assert payload["member"]["membership_status"] == MembershipStatus.ACTIVE

    login = client.post("/api/v1/auth/login", json={"username": "inline_user", "password": "12345678"})
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True

    invites = client.get("/api/v1/group-invites", headers={"Authorization": f"Bearer {login.json()['tokens']['access_token']}"})
    assert invites.status_code == 200
    assert invites.json() == []

    members = client.get(
        f"/api/v1/members?group_id={group['id']}",
        headers={"Authorization": f"Bearer {login.json()['tokens']['access_token']}"},
    )
    assert members.status_code == 200
    assert sorted(item["username"] for item in members.json()) == ["inline_user", "owner"]


def test_member_suggestions_return_matching_users(client, seeded_users):
    owner = seeded_users["owner"]
    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()

    response = client.get(
        f"/api/v1/members/suggestions?group_id={group['id']}&query=ali",
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": seeded_users["alice"]["user"]["id"],
            "username": "alice",
            "name": "Alice",
        }
    ]


def test_member_suggestions_exclude_existing_group_members(client, db_session, seeded_users):
    owner = seeded_users["owner"]
    alice = seeded_users["alice"]["user"]
    low_id, high_id = sorted((owner["user"]["id"], alice["id"]))
    db_session.add(UserConnection(user_low_id=low_id, user_high_id=high_id))
    db_session.commit()

    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    created = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    )
    assert created.status_code == 201

    response = client.get(
        f"/api/v1/members/suggestions?group_id={group['id']}&query=ali",
        headers=owner["headers"],
    )

    assert response.status_code == 200
    assert response.json() == []


def test_member_suggestions_return_empty_for_short_or_blank_query(client, seeded_users):
    owner = seeded_users["owner"]
    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()

    short_response = client.get(
        f"/api/v1/members/suggestions?group_id={group['id']}&query=al",
        headers=owner["headers"],
    )
    blank_response = client.get(
        f"/api/v1/members/suggestions?group_id={group['id']}&query=%20%20%20",
        headers=owner["headers"],
    )

    assert short_response.status_code == 200
    assert short_response.json() == []
    assert blank_response.status_code == 200
    assert blank_response.json() == []


def test_member_suggestions_require_group_access(client, seeded_group, second_account):
    response = client.get(
        f"/api/v1/members/suggestions?group_id={seeded_group['group']['id']}&query=ali",
        headers=second_account["headers"],
    )

    assert response.status_code == 404


def test_member_add_connected_user_is_immediate(client, db_session, seeded_users):
    owner = seeded_users["owner"]
    alice = seeded_users["alice"]["user"]
    low_id, high_id = sorted((owner["user"]["id"], alice["id"]))
    db_session.add(UserConnection(user_low_id=low_id, user_high_id=high_id))
    db_session.commit()

    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    created = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["outcome"] == "added"
    assert payload["member"]["username"] == "alice"
    assert payload["member"]["membership_status"] == MembershipStatus.ACTIVE


def test_member_add_unconnected_user_sends_invite(client, seeded_users):
    owner = seeded_users["owner"]
    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    created = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["outcome"] == "invite_sent"
    assert payload["member"]["membership_status"] == MembershipStatus.PENDING_INVITE

    invites = client.get("/api/v1/group-invites", headers=seeded_users["alice"]["headers"])
    assert invites.status_code == 200
    assert len(invites.json()) == 1
    assert invites.json()[0]["group_id"] == group["id"]


def test_accepting_invite_adds_group_access_and_connection(client, db_session, seeded_users):
    owner = seeded_users["owner"]
    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    member_response = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    ).json()
    invite = client.get("/api/v1/group-invites", headers=seeded_users["alice"]["headers"]).json()[0]

    accepted = client.post(f"/api/v1/group-invites/{invite['id']}/accept", headers=seeded_users["alice"]["headers"])
    assert accepted.status_code == 200
    assert accepted.json()["status"] == GroupInviteStatus.ACCEPTED

    alice_groups = client.get("/api/v1/groups", headers=seeded_users["alice"]["headers"])
    assert alice_groups.status_code == 200
    assert alice_groups.json()[0]["id"] == group["id"]

    members = client.get(f"/api/v1/members?group_id={group['id']}", headers=seeded_users["alice"]["headers"])
    assert members.status_code == 200
    assert sorted(item["username"] for item in members.json()) == ["alice", "owner"]

    owner_member_add = client.post(
        "/api/v1/groups",
        headers=seeded_users["alice"]["headers"],
        json={"name": "Shared 2"},
    ).json()
    added_again = client.post(
        "/api/v1/members",
        headers=seeded_users["alice"]["headers"],
        json={"group_id": owner_member_add["id"], "username": "owner", "is_archived": False},
    )
    assert added_again.status_code == 201
    assert added_again.json()["outcome"] == "added"

    connections = db_session.query(UserConnection).all()
    assert len(connections) == 1
    assert member_response["member"]["membership_status"] == MembershipStatus.PENDING_INVITE


def test_rejecting_invite_removes_pending_access(client, db_session, seeded_users):
    owner = seeded_users["owner"]
    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    created = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    ).json()
    invite = client.get("/api/v1/group-invites", headers=seeded_users["alice"]["headers"]).json()[0]

    rejected = client.post(f"/api/v1/group-invites/{invite['id']}/reject", headers=seeded_users["alice"]["headers"])
    assert rejected.status_code == 200
    assert rejected.json()["status"] == GroupInviteStatus.REJECTED

    pending_members = client.get(f"/api/v1/members?group_id={group['id']}", headers=owner["headers"]).json()
    assert pending_members == []
    assert db_session.query(GroupInvite).filter(GroupInvite.id == invite["id"]).one().status == GroupInviteStatus.REJECTED

    re_added = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    )
    assert re_added.status_code == 201
    assert re_added.json()["outcome"] == "invite_sent"
    assert created["member"]["id"] != re_added.json()["member"]["id"]


def test_readding_removed_connected_member_creates_new_row_without_touching_old_expenses(client, seeded_users):
    owner = seeded_users["owner"]
    alice = seeded_users["alice"]

    group = client.post("/api/v1/groups", headers=owner["headers"], json={"name": "Trip"}).json()
    invited = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    ).json()
    invite = client.get("/api/v1/group-invites", headers=alice["headers"]).json()[0]
    accepted = client.post(f"/api/v1/group-invites/{invite['id']}/accept", headers=alice["headers"]).json()

    expense = client.post(
        "/api/v1/expenses",
        headers=owner["headers"],
        json={
            "group_id": group["id"],
            "title": "Dinner",
            "note": None,
            "total_amount": 100,
            "split_type": "EXACT",
            "payers": [{"member_id": accepted["member_id"], "amount": 100}],
            "shares": [{"member_id": accepted["member_id"], "amount": 100}],
        },
    )
    assert expense.status_code == 201

    deleted = client.delete(f"/api/v1/members/{invited['member']['id']}", headers=owner["headers"])
    assert deleted.status_code == 204

    re_added = client.post(
        "/api/v1/members",
        headers=owner["headers"],
        json={"group_id": group["id"], "username": "alice", "is_archived": False},
    )
    assert re_added.status_code == 201
    payload = re_added.json()
    assert payload["outcome"] == "added"
    assert payload["member"]["membership_status"] == MembershipStatus.ACTIVE
    assert payload["member"]["id"] != invited["member"]["id"]

    groups = client.get("/api/v1/groups", headers=owner["headers"])
    assert groups.status_code == 200
    assert groups.json()[0]["id"] == group["id"]

    expenses = client.get(f"/api/v1/expenses?group_id={group['id']}", headers=owner["headers"])
    assert expenses.status_code == 200
    assert expenses.json()[0]["payers"][0]["member_id"] == invited["member"]["id"]


def test_non_member_cannot_access_shared_group_data(client, seeded_group, second_account):
    response = client.get(f"/api/v1/groups/{seeded_group['group']['id']}", headers=second_account["headers"])
    assert response.status_code == 404
    assert client.get(f"/api/v1/expenses?group_id={seeded_group['group']['id']}", headers=second_account["headers"]).status_code == 404

    accepted_invite = client.get("/api/v1/group-invites", headers=second_account["headers"])
    assert accepted_invite.status_code == 200
    assert accepted_invite.json() == []


def test_expense_crud(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]
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


def test_settlement_crud(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]
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


def test_group_card_crud(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]

    created = client.post(
        "/api/v1/group-cards",
        headers=auth_headers,
        json={"group_id": group["id"], "member_id": alice["id"], "card_number": "6037 9918 9975 4321"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["card_number"] == "6037991899754321"
    assert payload["member_id"] == alice["id"]

    listing = client.get(f"/api/v1/group-cards?group_id={group['id']}", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    updated = client.patch(
        f"/api/v1/group-cards/{payload['id']}",
        headers=auth_headers,
        json={"member_id": bob["id"], "card_number": "۵۰۲۲۲۹۱۰۷۳۷۷۹۹۹۹"},
    )
    assert updated.status_code == 200
    assert updated.json()["card_number"] == "5022291073779999"
    assert updated.json()["member_id"] == bob["id"]

    deleted = client.delete(f"/api/v1/group-cards/{payload['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/group-cards?group_id={group['id']}", headers=auth_headers).json() == []


def test_group_card_requires_active_member_and_unique_number(client, seeded_group, db_session):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]
    outsider_group = client.post("/api/v1/groups", headers=auth_headers, json={"name": "Other"}).json()
    outsider_member = client.get(f"/api/v1/members?group_id={outsider_group['id']}", headers=auth_headers).json()[0]

    first = client.post(
        "/api/v1/group-cards",
        headers=auth_headers,
        json={"group_id": group["id"], "member_id": alice["id"], "card_number": "6037991899754321"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/group-cards",
        headers=auth_headers,
        json={"group_id": group["id"], "member_id": bob["id"], "card_number": "6037-9918-9975-4321"},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["error"]["code"] == "duplicate_group_card"

    invalid_member = client.post(
        "/api/v1/group-cards",
        headers=auth_headers,
        json={"group_id": group["id"], "member_id": outsider_member["id"], "card_number": "5022291073779999"},
    )
    assert invalid_member.status_code == 400
    assert invalid_member.json()["error"]["code"] == "invalid_group_card_member"

    pending = client.post(
        "/api/v1/members",
        headers=auth_headers,
        json={"group_id": group["id"], "username": "second", "is_archived": False},
    ).json()["member"]
    invalid_pending = client.post(
        "/api/v1/group-cards",
        headers=auth_headers,
        json={"group_id": group["id"], "member_id": pending["id"], "card_number": "6274121200000000"},
    )
    assert invalid_pending.status_code == 400
    assert invalid_pending.json()["error"]["code"] == "invalid_group_card_member"

    invalid_number = client.post(
        "/api/v1/group-cards",
        headers=auth_headers,
        json={"group_id": group["id"], "member_id": alice["id"], "card_number": "1234"},
    )
    assert invalid_number.status_code == 400
    assert invalid_number.json()["error"]["code"] == "invalid_group_card"

    stored = db_session.query(GroupCard).filter(GroupCard.group_id == group["id"]).all()
    assert len(stored) == 1


def test_non_member_cannot_access_group_cards(client, seeded_group, second_account):
    created = client.post(
        "/api/v1/group-cards",
        headers=seeded_group["users"]["owner"]["headers"],
        json={
            "group_id": seeded_group["group"]["id"],
            "member_id": seeded_group["members"][0]["id"],
            "card_number": "6037991899754321",
        },
    ).json()

    listing = client.get(f"/api/v1/group-cards?group_id={seeded_group['group']['id']}", headers=second_account["headers"])
    assert listing.status_code == 404

    detail = client.get(f"/api/v1/group-cards/{created['id']}", headers=second_account["headers"])
    assert detail.status_code == 404
