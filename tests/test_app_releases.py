from __future__ import annotations

from app.core.config import get_settings
from app.models.domain import AppDownloadContent


def admin_headers(client) -> dict[str, str]:
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"username": "panel_admin", "password": "super-secret"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_can_create_upload_publish_and_list_app_release(client, tmp_path, db_session) -> None:
    settings = get_settings()
    settings.file_storage_local_dir = str(tmp_path)
    settings.file_storage_public_base_url = "https://cdn.example.com/files"
    headers = admin_headers(client)

    created = client.post(
        "/api/v1/admin/app-releases",
        headers=headers,
        json={
            "version_name": "1.4.0",
            "version_code": 42,
            "title": "دانلود اپلیکیشن",
            "subtitle": "آخرین نسخه دنگینو را از کافه بازار، مایکت یا لینک مستقیم نصب کن.",
            "app_icon_url": "https://splitwise.ir/android-chrome-512x512.png",
            "release_date": "2026-05-30",
            "file_size": "18.4 MB",
            "bazaar_url": "https://cafebazaar.ir/app/com.encer.splitwise",
            "myket_url": "https://myket.ir/app/com.encer.splitwise",
            "release_notes": ["بهبود پایداری", "رفع خطاهای دانلود"],
            "primary_badge_text": "نسخه جدید",
            "min_supported_version_code": 12,
            "update_mode": "soft",
            "update_title": "نسخه جدید آماده است",
            "update_message": "برای نصب نسخه جدید روی لینک دانلود بزن.",
        },
    )
    assert created.status_code == 201
    release_id = created.json()["id"]

    upload = client.post(
        f"/api/v1/admin/app-releases/{release_id}/apk",
        headers=headers,
        files={"file": ("release.apk", b"apk-content", "application/vnd.android.package-archive")},
    )
    assert upload.status_code == 200
    assert upload.json() == {
        "id": release_id,
        "filename": "app-release_1.4.0.apk",
        "apk_object_key": "app-releases/app-release_1.4.0.apk",
        "apk_url": "https://cdn.example.com/files/app-releases/app-release_1.4.0.apk",
    }
    assert (tmp_path / "app-releases" / "app-release_1.4.0.apk").read_bytes() == b"apk-content"

    published = client.post(f"/api/v1/admin/app-releases/{release_id}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["is_published"] is True

    public_download = client.get("/api/v1/app-download")
    assert public_download.status_code == 200
    assert public_download.json()["version_name"] == "1.4.0"
    assert public_download.json()["direct_download_url"] == "https://cdn.example.com/files/app-releases/app-release_1.4.0.apk"
    assert public_download.json()["bazaar_url"] == "https://cafebazaar.ir/app/com.encer.splitwise"
    assert public_download.json()["primary_badge_text"] == "نسخه جدید"
    assert public_download.json()["is_direct_download_enabled"] is True

    setting = client.get("/api/v1/site-settings")
    assert setting.status_code == 200
    assert setting.json()["apk_url"] == "https://cdn.example.com/files/app-releases/app-release_1.4.0.apk"

    listing = client.get("/api/v1/admin/app-releases", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["items"][0]["is_published"] is True
    assert listing.json()["items"][0]["apk_url"] == "https://cdn.example.com/files/app-releases/app-release_1.4.0.apk"

    record = db_session.query(AppDownloadContent).filter_by(slug="app_download").one()
    assert record.direct_download_url == "https://cdn.example.com/files/app-releases/app-release_1.4.0.apk"


def test_admin_app_release_apk_rejects_non_apk(client, tmp_path) -> None:
    get_settings().file_storage_local_dir = str(tmp_path)
    headers = admin_headers(client)
    created = client.post(
        "/api/v1/admin/app-releases",
        headers=headers,
        json={"version_name": "1.4.0", "version_code": 42, "release_notes": ["تست"]},
    )
    assert created.status_code == 201

    upload = client.post(
        f"/api/v1/admin/app-releases/{created.json()['id']}/apk",
        headers=headers,
        files={"file": ("release.zip", b"content", "application/zip")},
    )

    assert upload.status_code == 400
    assert upload.json()["error"]["code"] == "invalid_app_release_apk"
