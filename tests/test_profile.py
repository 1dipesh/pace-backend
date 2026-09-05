from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_profile_crud() -> None:
    # Ensure a previous test run does not leave an active profile behind.
    client.delete("/api/v1/profile")

    payload = {
        "date_of_birth": "1990-12-20",
        "height_cm": 178,
        "weight_kg": 78,
        "calorie_estimate_sex": "male",
        "goal": "build_muscle",
        "activity_level": "active",
        "training_experience": "intermediate",
        "training_days_per_week": 4,
    }

    created = client.post("/api/v1/profile", json=payload)
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["goal"] == "build_muscle"
    assert created_body["age"] >= 18
    assert created_body["version"] >= 1

    fetched = client.get("/api/v1/profile")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == created_body["id"]

    updated = client.patch(
        "/api/v1/profile",
        json={"weight_kg": 79.5, "goal": "improve_performance"},
    )
    assert updated.status_code == 200
    assert updated.json()["weight_kg"] == 79.5
    assert updated.json()["goal"] == "improve_performance"
    assert updated.json()["version"] == created_body["version"] + 1

    deleted = client.delete("/api/v1/profile")
    assert deleted.status_code == 204

    missing = client.get("/api/v1/profile")
    assert missing.status_code == 404
