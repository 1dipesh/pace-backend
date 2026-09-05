import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_nutrition_vertical_slice() -> None:
    suffix = uuid.uuid4().hex[:8]
    logged_date = "2026-09-05"

    goals = client.put(
        "/api/v1/nutrition/goals",
        json={
            "target_calories_kcal": 2200,
            "target_protein_g": 160,
            "target_carbs_g": 240,
            "target_fat_g": 70,
            "target_fiber_g": 30,
        },
    )
    assert goals.status_code == 200
    assert goals.json()["target_protein_g"] == 160

    food = client.post(
        "/api/v1/nutrition/foods",
        json={
            "name": f"Test chicken {suffix}",
            "basis_amount": 100,
            "basis_unit": "g",
            "calories_kcal": 165,
            "protein_g": 31,
            "carbs_g": 0,
            "fat_g": 3.6,
            "fiber_g": 0,
            "preparation_state": "cooked",
            "source": "custom",
            "is_favorite": True,
        },
    )
    assert food.status_code == 201
    food_id = food.json()["id"]

    first_entry = client.post(
        "/api/v1/nutrition/entries",
        json={
            "logged_date": logged_date,
            "meal_type": "lunch",
            "food_id": food_id,
            "amount": 150,
            "unit": "g",
        },
    )
    assert first_entry.status_code == 201
    assert first_entry.json()["calories_kcal"] == 247.5
    first_entry_id = first_entry.json()["id"]

    # Changing a reusable food must not rewrite an existing historical entry snapshot.
    changed_food = client.patch(
        f"/api/v1/nutrition/foods/{food_id}",
        json={"calories_kcal": 170},
    )
    assert changed_food.status_code == 200

    historical_entry = client.get(f"/api/v1/nutrition/entries/{first_entry_id}")
    assert historical_entry.status_code == 200
    assert historical_entry.json()["calories_kcal"] == 247.5

    # Editing the logged amount scales its own snapshot, not the now-changed food definition.
    resized_entry = client.patch(
        f"/api/v1/nutrition/entries/{first_entry_id}",
        json={"amount": 300},
    )
    assert resized_entry.status_code == 200
    assert resized_entry.json()["calories_kcal"] == 495.0

    saved_meal = client.post(
        "/api/v1/nutrition/saved-meals",
        json={
            "name": f"Test saved meal {suffix}",
            "items": [{"food_id": food_id, "amount": 200, "unit": "g"}],
        },
    )
    assert saved_meal.status_code == 201
    saved_meal_id = saved_meal.json()["id"]
    assert saved_meal.json()["totals"]["calories_kcal"] == 340.0

    # Saved meals reference foods, so a future log uses the current food definition.
    logged_meal = client.post(
        f"/api/v1/nutrition/saved-meals/{saved_meal_id}/log",
        json={"logged_date": logged_date, "meal_type": "dinner"},
    )
    assert logged_meal.status_code == 201
    assert logged_meal.json()[0]["calories_kcal"] == 340.0
    logged_meal_entry_id = logged_meal.json()[0]["id"]

    manual_entry = client.post(
        "/api/v1/nutrition/entries",
        json={
            "logged_date": logged_date,
            "meal_type": "snack",
            "manual": {
                "name": f"One-time food {suffix}",
                "amount": 1,
                "unit": "serving",
                "calories_kcal": 300,
                "protein_g": 10,
                "carbs_g": 35,
                "fat_g": 12,
            },
        },
    )
    assert manual_entry.status_code == 201
    manual_entry_id = manual_entry.json()["id"]
    assert manual_entry.json()["source_food_id"] is None

    summary = client.get(f"/api/v1/nutrition/daily/{logged_date}")
    assert summary.status_code == 200
    summary_ids = {entry["id"] for entry in summary.json()["entries"]}
    assert {first_entry_id, logged_meal_entry_id, manual_entry_id}.issubset(summary_ids)

    # Clean up the user-owned test records. Goals remain as the dev user's current test goals.
    assert client.delete(f"/api/v1/nutrition/entries/{first_entry_id}").status_code == 204
    assert client.delete(f"/api/v1/nutrition/entries/{logged_meal_entry_id}").status_code == 204
    assert client.delete(f"/api/v1/nutrition/entries/{manual_entry_id}").status_code == 204
    assert client.delete(f"/api/v1/nutrition/saved-meals/{saved_meal_id}").status_code == 204
    assert client.delete(f"/api/v1/nutrition/foods/{food_id}").status_code == 204
