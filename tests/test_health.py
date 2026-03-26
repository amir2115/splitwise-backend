from app.api import health as health_api
from app.main import settings as main_settings


def test_health_defaults(client):
    health_api.settings.app_min_supported_version_code = None
    health_api.settings.app_latest_version_code = None
    health_api.settings.app_update_mode = "none"
    health_api.settings.app_update_store_url = None
    health_api.settings.app_update_title = None
    health_api.settings.app_update_message = None

    main_settings.app_min_supported_version_code = None
    main_settings.app_latest_version_code = None
    main_settings.app_update_mode = "none"
    main_settings.app_update_store_url = None
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
    health_api.settings.app_update_title = "به‌روزرسانی اجباری"
    health_api.settings.app_update_message = "برای ادامه نسخه جدید را نصب کن."

    main_settings.app_min_supported_version_code = 12
    main_settings.app_latest_version_code = 18
    main_settings.app_update_mode = "hard"
    main_settings.app_update_store_url = "https://cafebazaar.ir/app/com.encer.offlinesplitwise"
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
