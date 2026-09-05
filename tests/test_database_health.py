import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_database_health() -> None:
    response = client.get("/health/database")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "postgresql"}
