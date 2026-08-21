from fastapi.testclient import TestClient

from app.main import app, settings


def test_health() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": settings.app_env}
