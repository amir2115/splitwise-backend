from app.api import app_download as app_download_api


def setup_function() -> None:
    app_download_api.settings.app_download_admin_secret = None


def seed_app_download(client, **overrides):
    app_download_api.settings.app_download_admin_secret = "top-secret"
    payload = {
        "title": "دانلود اپلیکیشن",
        "subtitle": "آخرین نسخه را از مسیر دلخواه نصب کن.",
        "version_name": "1.4.0",
        "version_code": 42,
        "min_supported_version_code": 12,
        "update_mode": "hard",
        "update_title": "به‌روزرسانی اجباری",
        "update_message": "برای ادامه نسخه جدید را نصب کن.",
        "bazaar_url": "https://cafebazaar.ir/app/com.encer.offlinesplitwise",
        "myket_url": "https://myket.ir/app/com.encer.offlinesplitwise",
        "direct_download_url": "https://splitwise.ir/files/app.apk",
        "release_notes": ["بهبود پایداری همگام‌سازی"],
    }
    payload.update(overrides)
    response = client.patch(
        "/api/v1/admin/app-download",
        headers={"X-Admin-Secret": "top-secret"},
        json=payload,
    )
    assert response.status_code == 200
    return response.json()


def test_health_defaults_without_record(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "min_supported_version_code": None,
        "latest_version_code": None,
        "update_mode": None,
        "store_url": None,
        "update_title": None,
        "update_message": None,
    }


def test_health_exposes_update_policy_from_app_download_record(client):
    seed_app_download(client)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "min_supported_version_code": 12,
        "latest_version_code": 42,
        "update_mode": "hard",
        "store_url": "https://splitwise.ir/files/app.apk",
        "update_title": "به‌روزرسانی اجباری",
        "update_message": "برای ادامه نسخه جدید را نصب کن.",
    }


def test_health_uses_store_specific_url_from_header_with_fallbacks(client):
    seed_app_download(client, bazaar_url=None)

    bazaar_response = client.get("/api/v1/health", headers={"X-App-Store": "bazaar"})
    myket_response = client.get("/api/v1/health", headers={"X-App-Store": "myket"})
    organic_response = client.get("/api/v1/health", headers={"X-App-Store": "organic"})
    invalid_response = client.get("/api/v1/health", headers={"X-App-Store": "unknown"})

    assert bazaar_response.status_code == 200
    assert myket_response.status_code == 200
    assert organic_response.status_code == 200
    assert invalid_response.status_code == 200
    assert bazaar_response.json()["store_url"] == "https://splitwise.ir/files/app.apk"
    assert myket_response.json()["store_url"] == "https://myket.ir/app/com.encer.offlinesplitwise"
    assert organic_response.json()["store_url"] == "https://splitwise.ir/files/app.apk"
    assert invalid_response.json()["store_url"] == "https://splitwise.ir/files/app.apk"


def test_health_falls_back_to_first_available_link_when_direct_link_is_missing(client):
    seed_app_download(
        client,
        bazaar_url="https://cafebazaar.ir/app/com.encer.offlinesplitwise",
        myket_url=None,
        direct_download_url=None,
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["store_url"] == "https://cafebazaar.ir/app/com.encer.offlinesplitwise"


def test_health_returns_null_mode_when_update_mode_is_none(client):
    seed_app_download(
        client,
        update_mode="none",
        update_title="نسخه جدید آماده است",
        update_message="هر وقت خواستی به‌روزرسانی کن.",
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["update_mode"] is None
    assert response.json()["update_title"] == "نسخه جدید آماده است"
    assert response.json()["update_message"] == "هر وقت خواستی به‌روزرسانی کن."


def test_root_health_matches_api_health(client):
    seed_app_download(client, update_mode="soft", min_supported_version_code=10)

    root_response = client.get("/health", headers={"X-App-Store": "myket"})
    api_response = client.get("/api/v1/health", headers={"X-App-Store": "myket"})

    assert root_response.status_code == 200
    assert api_response.status_code == 200
    assert root_response.json() == api_response.json()
