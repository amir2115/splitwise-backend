from pathlib import Path

from app.api import app_download as app_download_api


def setup_function() -> None:
    app_download_api.settings.app_download_admin_secret = None
    app_download_api.settings.app_download_upload_dir = "/files"
    app_download_api.settings.app_download_public_base_url = "https://api.splitwise.ir"


def test_get_app_download_returns_neutral_payload_without_record(client):
    response = client.get("/api/v1/app-download")

    assert response.status_code == 200
    assert response.json() == {
        "title": "دانلود اپلیکیشن",
        "subtitle": "آخرین نسخه دنگینو را از استور دلخواهت نصب کن.",
        "app_icon_url": None,
        "version_name": None,
        "version_code": None,
        "release_date": None,
        "file_size": None,
        "bazaar_url": None,
        "myket_url": None,
        "direct_download_url": None,
        "release_notes": [],
        "primary_badge_text": None,
        "min_supported_version_code": None,
        "update_mode": None,
        "update_title": None,
        "update_message": None,
        "is_direct_download_enabled": False,
    }


def test_patch_app_download_persists_content(client):
    app_download_api.settings.app_download_admin_secret = "top-secret"

    response = client.patch(
        "/api/v1/admin/app-download",
        headers={"X-Admin-Secret": "top-secret"},
        json={
            "title": "دانلود اپلیکیشن",
            "subtitle": "آخرین نسخه را از مسیر دلخواه نصب کن.",
            "app_icon_url": "https://splitwise.ir/assets/app-icon.png",
            "version_name": "1.4.0",
            "version_code": 42,
            "release_date": "2026-03-27",
            "file_size": "18.4 MB",
            "bazaar_url": "https://cafebazaar.ir/app/com.encer.offlinesplitwise",
            "myket_url": "https://myket.ir/app/com.encer.offlinesplitwise",
            "direct_download_url": "https://splitwise.ir/files/app.apk",
            "release_notes": ["بهبود پایداری همگام‌سازی", "رفع مشکل ثبت هزینه"],
            "primary_badge_text": "نسخه جدید",
            "min_supported_version_code": 12,
            "update_mode": "hard",
            "update_title": "به‌روزرسانی اجباری",
            "update_message": "برای ادامه نسخه جدید را نصب کن.",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "title": "دانلود اپلیکیشن",
        "subtitle": "آخرین نسخه را از مسیر دلخواه نصب کن.",
        "app_icon_url": "https://splitwise.ir/assets/app-icon.png",
        "version_name": "1.4.0",
        "version_code": 42,
        "release_date": "2026-03-27",
        "file_size": "18.4 MB",
        "bazaar_url": "https://cafebazaar.ir/app/com.encer.offlinesplitwise",
        "myket_url": "https://myket.ir/app/com.encer.offlinesplitwise",
        "direct_download_url": "https://splitwise.ir/files/app.apk",
        "release_notes": ["بهبود پایداری همگام‌سازی", "رفع مشکل ثبت هزینه"],
        "primary_badge_text": "نسخه جدید",
        "min_supported_version_code": 12,
        "update_mode": "hard",
        "update_title": "به‌روزرسانی اجباری",
        "update_message": "برای ادامه نسخه جدید را نصب کن.",
        "is_direct_download_enabled": True,
    }

    get_response = client.get("/api/v1/app-download")
    assert get_response.status_code == 200
    assert get_response.json()["version_name"] == "1.4.0"
    assert get_response.json()["release_notes"] == ["بهبود پایداری همگام‌سازی", "رفع مشکل ثبت هزینه"]
    assert get_response.json()["update_mode"] == "hard"
    assert get_response.json()["min_supported_version_code"] == 12


def test_patch_app_download_allows_single_direct_link(client):
    app_download_api.settings.app_download_admin_secret = "top-secret"

    response = client.patch(
        "/api/v1/admin/app-download",
        headers={"X-Admin-Secret": "top-secret"},
        json={
            "title": "دانلود اپلیکیشن",
            "subtitle": "نسخه مستقیم برای دانلود آماده است.",
            "direct_download_url": "https://splitwise.ir/files/app.apk",
            "release_notes": ["رفع باگ‌های عمومی"],
            "update_mode": "soft",
            "update_title": "نسخه جدید آماده است",
            "update_message": "برای نصب نسخه جدید روی لینک دانلود بزن.",
        },
    )

    assert response.status_code == 200
    assert response.json()["bazaar_url"] is None
    assert response.json()["myket_url"] is None
    assert response.json()["direct_download_url"] == "https://splitwise.ir/files/app.apk"
    assert response.json()["is_direct_download_enabled"] is True
    assert response.json()["update_mode"] == "soft"


def test_patch_app_download_requires_valid_secret(client):
    app_download_api.settings.app_download_admin_secret = "top-secret"

    response = client.patch(
        "/api/v1/admin/app-download",
        headers={"X-Admin-Secret": "wrong-secret"},
        json={"title": "دانلود اپلیکیشن"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_app_download_admin_secret"


def test_patch_app_download_validates_release_notes(client):
    app_download_api.settings.app_download_admin_secret = "top-secret"

    response = client.patch(
        "/api/v1/admin/app-download",
        headers={"X-Admin-Secret": "top-secret"},
        json={
            "title": "دانلود اپلیکیشن",
            "subtitle": "بدون notes نباید ذخیره شود.",
            "direct_download_url": "https://splitwise.ir/files/app.apk",
            "release_notes": [],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_app_download_content"


def test_patch_app_download_validates_urls(client):
    app_download_api.settings.app_download_admin_secret = "top-secret"

    response = client.patch(
        "/api/v1/admin/app-download",
        headers={"X-Admin-Secret": "top-secret"},
        json={
            "title": "دانلود اپلیکیشن",
            "subtitle": "لینک نامعتبر نباید ذخیره شود.",
            "direct_download_url": "not-a-url",
            "release_notes": ["تست اعتبارسنجی"],
        },
    )

    assert response.status_code == 422


def test_patch_app_download_validates_update_mode(client):
    app_download_api.settings.app_download_admin_secret = "top-secret"

    response = client.patch(
        "/api/v1/admin/app-download",
        headers={"X-Admin-Secret": "top-secret"},
        json={
            "title": "دانلود اپلیکیشن",
            "subtitle": "مود نامعتبر نباید ذخیره شود.",
            "direct_download_url": "https://splitwise.ir/files/app.apk",
            "release_notes": ["تست اعتبارسنجی"],
            "update_mode": "force",
        },
    )

    assert response.status_code == 422


def test_upload_app_download_apk_persists_file_and_returns_direct_link(client, tmp_path):
    app_download_api.settings.app_download_admin_secret = "top-secret"
    app_download_api.settings.app_download_upload_dir = str(tmp_path)
    app_download_api.settings.app_download_public_base_url = "https://api.splitwise.ir"

    response = client.post(
        "/api/v1/admin/app-download/apk",
        headers={"X-Admin-Secret": "top-secret"},
        files={"file": ("custom-name.apk", b"apk-binary-content", "application/vnd.android.package-archive")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "app-organic-release.apk",
        "stored_path": str(tmp_path / "app-organic-release.apk"),
        "direct_download_url": "https://api.splitwise.ir/files/app-organic-release.apk",
    }
    assert (tmp_path / "app-organic-release.apk").read_bytes() == b"apk-binary-content"


def test_uploaded_apk_is_served_from_backend_files_route(client, tmp_path):
    app_download_api.settings.app_download_admin_secret = "top-secret"
    app_download_api.settings.app_download_upload_dir = str(tmp_path)

    upload_response = client.post(
        "/api/v1/admin/app-download/apk",
        headers={"X-Admin-Secret": "top-secret"},
        files={"file": ("release.apk", b"apk-binary-content", "application/vnd.android.package-archive")},
    )

    assert upload_response.status_code == 200

    download_response = client.get("/files/app-organic-release.apk")

    assert download_response.status_code == 200
    assert download_response.content == b"apk-binary-content"
    assert download_response.headers["content-type"] == "application/vnd.android.package-archive"


def test_upload_app_download_apk_overwrites_existing_file(client, tmp_path):
    app_download_api.settings.app_download_admin_secret = "top-secret"
    app_download_api.settings.app_download_upload_dir = str(tmp_path)
    existing_file = Path(tmp_path / "app-organic-release.apk")
    existing_file.write_bytes(b"old-content")

    response = client.post(
        "/api/v1/admin/app-download/apk",
        headers={"X-Admin-Secret": "top-secret"},
        files={"file": ("release.apk", b"new-content", "application/vnd.android.package-archive")},
    )

    assert response.status_code == 200
    assert existing_file.read_bytes() == b"new-content"


def test_upload_app_download_apk_requires_valid_secret(client, tmp_path):
    app_download_api.settings.app_download_admin_secret = "top-secret"
    app_download_api.settings.app_download_upload_dir = str(tmp_path)

    response = client.post(
        "/api/v1/admin/app-download/apk",
        headers={"X-Admin-Secret": "wrong-secret"},
        files={"file": ("release.apk", b"content", "application/vnd.android.package-archive")},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_app_download_admin_secret"


def test_upload_app_download_apk_rejects_non_apk_extension(client, tmp_path):
    app_download_api.settings.app_download_admin_secret = "top-secret"
    app_download_api.settings.app_download_upload_dir = str(tmp_path)

    response = client.post(
        "/api/v1/admin/app-download/apk",
        headers={"X-Admin-Secret": "top-secret"},
        files={"file": ("release.zip", b"content", "application/zip")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_app_download_apk"
