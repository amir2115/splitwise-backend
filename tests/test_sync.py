from app.models.domain import GroupInvite, GroupInviteStatus, MembershipStatus


def test_first_login_local_import(client, auth_headers, second_account, db_session):
    imported = client.post(
        "/api/v1/sync/import",
        headers=auth_headers,
        json={
            "device_id": "device-1",
            "groups": [{"id": "group-1", "name": "Imported group", "updated_at": "2026-03-17T10:00:00Z"}],
            "members": [
                {
                    "id": "member-1",
                    "group_id": "group-1",
                    "username": "second",
                    "is_archived": False,
                    "updated_at": "2026-03-17T10:00:01Z",
                }
            ],
            "expenses": [],
            "settlements": [],
            "deleted_group_ids": [],
            "deleted_member_ids": [],
            "deleted_expense_ids": [],
            "deleted_settlement_ids": [],
        },
    )
    assert imported.status_code == 200
    groups = client.get("/api/v1/groups", headers=auth_headers).json()
    assert groups[0]["id"] == "group-1"
    invites = client.get("/api/v1/group-invites", headers=second_account["headers"]).json()
    assert invites[0]["group_id"] == "group-1"


def test_repeated_sync_with_no_changes(client, seeded_group):
    auth_headers = seeded_group["users"]["owner"]["headers"]
    first = client.post("/api/v1/sync", headers=auth_headers, json={"device_id": "device-1", "last_synced_at": None})
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]

    second = client.post("/api/v1/sync", headers=auth_headers, json={"device_id": "device-1", "last_synced_at": cursor})
    assert second.status_code == 200
    assert second.json()["changes"] == {
        "groups": [],
        "members": [],
        "expenses": [],
        "settlements": [],
        "deleted_group_ids": [],
        "deleted_member_ids": [],
        "deleted_expense_ids": [],
        "deleted_settlement_ids": [],
    }


def test_conflict_resolution_last_write_wins(client, seeded_group):
    group = seeded_group["group"]
    auth_headers = seeded_group["users"]["owner"]["headers"]
    response = client.post(
        "/api/v1/sync",
        headers=auth_headers,
        json={
            "device_id": "device-1",
            "last_synced_at": None,
            "push": {
                "device_id": "device-1",
                "groups": [{"id": group["id"], "name": "Older name", "updated_at": "2026-03-16T10:00:00Z"}],
                "members": [],
                "expenses": [],
                "settlements": [],
                "deleted_group_ids": [],
                "deleted_member_ids": [],
                "deleted_expense_ids": [],
                "deleted_settlement_ids": [],
            },
        },
    )
    assert response.status_code == 200
    assert client.get(f"/api/v1/groups/{group['id']}", headers=auth_headers).json()["name"] == "Trip"

    newer = client.post(
        "/api/v1/sync",
        headers=auth_headers,
        json={
            "device_id": "device-1",
            "last_synced_at": None,
            "push": {
                "device_id": "device-1",
                "groups": [{"id": group["id"], "name": "Newer name", "updated_at": "2099-03-17T10:00:00Z"}],
                "members": [],
                "expenses": [],
                "settlements": [],
                "deleted_group_ids": [],
                "deleted_member_ids": [],
                "deleted_expense_ids": [],
                "deleted_settlement_ids": [],
            },
        },
    )
    assert newer.status_code == 200
    assert client.get(f"/api/v1/groups/{group['id']}", headers=auth_headers).json()["name"] == "Newer name"


def test_delete_propagation_via_tombstones(client, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
    auth_headers = seeded_group["users"]["owner"]["headers"]
    expense = client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "group_id": group["id"],
            "title": "Brunch",
            "note": None,
            "total_amount": 200,
            "split_type": "EXACT",
            "payers": [{"member_id": alice["id"], "amount": 200}],
            "shares": [{"member_id": alice["id"], "amount": 100}, {"member_id": bob["id"], "amount": 100}],
        },
    ).json()
    cursor = client.post("/api/v1/sync", headers=auth_headers, json={"device_id": "device-1", "last_synced_at": None}).json()["next_cursor"]

    deleted = client.delete(f"/api/v1/expenses/{expense['id']}", headers=auth_headers)
    assert deleted.status_code == 204

    sync = client.post("/api/v1/sync", headers=auth_headers, json={"device_id": "device-1", "last_synced_at": cursor})
    assert sync.status_code == 200
    assert sync.json()["changes"]["deleted_expense_ids"] == [expense["id"]]


def test_sync_rejects_unknown_member_usernames(client, auth_headers):
    group = client.post("/api/v1/groups", headers=auth_headers, json={"name": "Trip"}).json()
    response = client.post(
        "/api/v1/sync",
        headers=auth_headers,
        json={
            "device_id": "device-1",
            "last_synced_at": None,
            "push": {
                "device_id": "device-1",
                "groups": [],
                "members": [
                    {
                        "id": "member-offline-1",
                        "group_id": group["id"],
                        "username": "missing_user",
                        "is_archived": False,
                        "updated_at": "2099-03-17T10:00:00Z",
                    }
                ],
                "expenses": [],
                "settlements": [],
                "deleted_group_ids": [],
                "deleted_member_ids": [],
                "deleted_expense_ids": [],
                "deleted_settlement_ids": [],
            },
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_member_usernames"
    assert response.json()["error"]["details"] == [{"member_id": "member-offline-1", "username": "missing_user"}]


def test_sync_creates_pending_invite_for_valid_disconnected_username(client, auth_headers, second_account, db_session):
    group = client.post("/api/v1/groups", headers=auth_headers, json={"name": "Trip"}).json()
    response = client.post(
        "/api/v1/sync",
        headers=auth_headers,
        json={
            "device_id": "device-1",
            "last_synced_at": None,
            "push": {
                "device_id": "device-1",
                "groups": [],
                "members": [
                    {
                        "id": "member-offline-1",
                        "group_id": group["id"],
                        "username": "second",
                        "is_archived": False,
                        "updated_at": "2099-03-17T10:00:00Z",
                    }
                ],
                "expenses": [],
                "settlements": [],
                "deleted_group_ids": [],
                "deleted_member_ids": [],
                "deleted_expense_ids": [],
                "deleted_settlement_ids": [],
            },
        },
    )
    assert response.status_code == 200

    owner_members = client.get(f"/api/v1/members?group_id={group['id']}", headers=auth_headers).json()
    assert owner_members[0]["membership_status"] == MembershipStatus.PENDING_INVITE
    assert owner_members[0]["username"] == "second"

    invites = client.get("/api/v1/group-invites", headers=second_account["headers"])
    assert invites.status_code == 200
    assert invites.json()[0]["status"] == GroupInviteStatus.PENDING
    assert db_session.query(GroupInvite).count() == 1
