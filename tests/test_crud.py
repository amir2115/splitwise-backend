from app.models.domain import GroupInvite, GroupInviteStatus, MembershipStatus, UserConnection


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
    assert created["member"]["id"] == re_added.json()["member"]["id"]


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
