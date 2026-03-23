from datetime import datetime, timedelta, timezone


def test_first_login_local_import(client, auth_headers):
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
                    "name": "Alice",
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


def test_repeated_sync_with_no_changes(client, auth_headers, seeded_group):
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


def test_conflict_resolution_last_write_wins(client, auth_headers, seeded_group):
    group = seeded_group["group"]
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


def test_delete_propagation_via_tombstones(client, auth_headers, seeded_group):
    group = seeded_group["group"]
    alice, bob, _ = seeded_group["members"]
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
