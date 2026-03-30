from unittest.mock import Mock

from sqlalchemy.exc import ProgrammingError

from app.services import health_service


def test_build_health_response_returns_ok_when_app_download_lookup_fails(monkeypatch):
    def broken_lookup(_db):
        raise ProgrammingError("select * from app_download_content", {}, Exception("missing relation"))

    monkeypatch.setattr(health_service, "get_app_download_record", broken_lookup)

    response = health_service.build_health_response(Mock(), "organic")

    assert response.status == "ok"
    assert response.min_supported_version_code is None
    assert response.latest_version_code is None
    assert response.update_mode is None
    assert response.store_url is None
