from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.nutrition import NutritionGoal
from app.models.user import PaceUser


client = TestClient(app)
HEADERS = {"Authorization": "Bearer user-a-token"}


def test_account_export_is_private_complete_and_user_scoped() -> None:
    profile = {
        "date_of_birth": "1990-12-20",
        "height_cm": 178,
        "weight_kg": 78,
        "calorie_estimate_sex": "male",
        "goal": "build_muscle",
        "activity_level": "active",
        "training_experience": "intermediate",
        "training_days_per_week": 4,
    }
    assert client.post("/api/v1/profile", json=profile, headers=HEADERS).status_code in (201, 409)
    assert client.put(
        "/api/v1/nutrition/goals",
        json={
            "target_calories_kcal": 2400,
            "target_protein_g": 160,
            "target_carbs_g": 260,
            "target_fat_g": 75,
            "target_fiber_g": 30,
        },
        headers=HEADERS,
    ).status_code == 200

    response = client.get("/api/v1/account/export", headers=HEADERS)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, private"
    body = response.json()
    assert body["format"] == "pace-account-export"
    assert body["format_version"] == 1
    assert body["account"]["email"] == "user-a@example.com"
    assert body["data"]["pace_profiles"]
    assert body["data"]["nutrition_goals"]
    assert "pace_sync_receipts" in body["data"]
    assert "auth_subject" not in body["account"]

    other = client.get("/api/v1/account/export", headers={"Authorization": "Bearer user-b-token"})
    assert other.status_code == 200
    assert other.json()["account"]["email"] == "user-b@example.com"
    assert other.json()["data"]["nutrition_goals"] == []


def test_account_deletion_requires_confirmation_and_removes_owned_rows() -> None:
    rejected = client.request("DELETE", "/api/v1/account", json={"confirmation": "delete"}, headers=HEADERS)
    assert rejected.status_code == 422

    response = client.request("DELETE", "/api/v1/account", json={"confirmation": "DELETE"}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    with SessionLocal() as db:
        assert db.scalar(select(PaceUser).where(PaceUser.email == "user-a@example.com")) is None
        assert db.scalars(select(NutritionGoal)).all() == []

    # Supabase identity is separate: signing in again provisions a fresh, empty Pace account.
    fresh = client.get("/api/v1/account/export", headers=HEADERS)
    assert fresh.status_code == 200
    assert fresh.json()["data"]["nutrition_goals"] == []
