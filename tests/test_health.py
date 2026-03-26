from app.api import health as health_api
from app.main import settings as main_settings


def test_health_defaults(client):
    health_api.settings.app_min_supported_version_code = None
    health_api.settings.app_latest_version_code = None
    health_api.settings.app_update_mode = "none"
    health_api.settings.app_update_store_url = None
    health_api.settings.app_update_bazaar_store_url = None
    health_api.settings.app_update_myket_store_url = None
    health_api.settings.app_update_title = None
    health_api.settings.app_update_message = None

    main_settings.app_min_supported_version_code = None
    main_settings.app_latest_version_code = None
    main_settings.app_update_mode = "none"
    main_settings.app_update_store_url = None
    main_settings.app_update_bazaar_store_url = None
    main_settings.app_update_myket_store_url = None
    main_settings.app_update_title = None
    main_settings.app_update_message = None

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


def test_health_exposes_update_policy(client):
    health_api.settings.app_min_supported_version_code = 12
    health_api.settings.app_latest_version_code = 18
    health_api.settings.app_update_mode = "hard"
    health_api.settings.app_update_store_url = "https://cafebazaar.ir/app/com.encer.offlinesplitwise"
    health_api.settings.app_update_bazaar_store_url = None
    health_api.settings.app_update_myket_store_url = None
    health_api.settings.app_update_title = "به‌روزرسانی اجباری"
    health_api.settings.app_update_message = "برای ادامه نسخه جدید را نصب کن."

    main_settings.app_min_supported_version_code = 12
    main_settings.app_latest_version_code = 18
    main_settings.app_update_mode = "hard"
    main_settings.app_update_store_url = "https://cafebazaar.ir/app/com.encer.offlinesplitwise"
    main_settings.app_update_bazaar_store_url = None
    main_settings.app_update_myket_store_url = None
    main_settings.app_update_title = "به‌روزرسانی اجباری"
    main_settings.app_update_message = "برای ادامه نسخه جدید را نصب کن."

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "min_supported_version_code": 12,
        "latest_version_code": 18,
        "update_mode": "hard",
        "store_url": "https://cafebazaar.ir/app/com.encer.offlinesplitwise",
        "update_title": "به‌روزرسانی اجباری",
        "update_message": "برای ادامه نسخه جدید را نصب کن.",
    }


def test_health_uses_store_specific_url_from_header(client):
    health_api.settings.app_min_supported_version_code = 12
    health_api.settings.app_latest_version_code = 18
    health_api.settings.app_update_mode = "soft"
    health_api.settings.app_update_store_url = "https://example.com/fallback"
    health_api.settings.app_update_bazaar_store_url = "https://cafebazaar.ir/app/com.encer.offlinesplitwise"
    health_api.settings.app_update_myket_store_url = "https://myket.ir/app/com.encer.offlinesplitwise"
    health_api.settings.app_update_title = "نسخه جدید آماده است"
    health_api.settings.app_update_message = "نسخه جدید را از استور خودت نصب کن."

    main_settings.app_min_supported_version_code = 12
    main_settings.app_latest_version_code = 18
    main_settings.app_update_mode = "soft"
    main_settings.app_update_store_url = "https://example.com/fallback"
    main_settings.app_update_bazaar_store_url = "https://cafebazaar.ir/app/com.encer.offlinesplitwise"
    main_settings.app_update_myket_store_url = "https://myket.ir/app/com.encer.offlinesplitwise"
    main_settings.app_update_title = "نسخه جدید آماده است"
    main_settings.app_update_message = "نسخه جدید را از استور خودت نصب کن."

    bazaar_response = client.get("/api/v1/health", headers={"X-App-Store": "bazaar"})
    myket_response = client.get("/api/v1/health", headers={"X-App-Store": "myket"})

    assert bazaar_response.status_code == 200
    assert myket_response.status_code == 200
    assert bazaar_response.json()["store_url"] == "https://cafebazaar.ir/app/com.encer.offlinesplitwise"
    assert myket_response.json()["store_url"] == "https://myket.ir/app/com.encer.offlinesplitwise"
