import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_alcohol_vertical_slice() -> None:
    suffix = uuid.uuid4().hex[:8]

    # Clean up any stale live session from an interrupted previous test run.
    active = client.get("/api/v1/alcohol/sessions/active")
    if active.status_code == 200:
        client.delete(f"/api/v1/alcohol/sessions/{active.json()['id']}")

    live = client.post(
        "/api/v1/alcohol/sessions",
        json={
            "entry_mode": "live",
            "started_at": "2026-09-05T18:00:00+07:00",
            "notes": f"Test live session {suffix}",
        },
    )
    assert live.status_code == 201
    session_id = live.json()["id"]
    assert live.json()["status"] == "active"

    duplicate_live = client.post(
        "/api/v1/alcohol/sessions",
        json={"entry_mode": "live", "started_at": "2026-09-05T18:05:00+07:00"},
    )
    assert duplicate_live.status_code == 409

    drink = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/drinks",
        json={
            "category": "beer",
            "name": f"Test Beer {suffix}",
            "volume_ml": 330,
            "abv_percent": 5,
            "logged_at": "2026-09-05T18:10:00+07:00",
        },
    )
    assert drink.status_code == 201
    drink_id = drink.json()["id"]
    assert drink.json()["alcohol_grams"] == pytest.approx(13.019, abs=0.001)

    water = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/water",
        json={"volume_ml": 500, "container": "bottle", "logged_at": "2026-09-05T18:20:00+07:00"},
    )
    assert water.status_code == 201
    assert water.json()["volume_ml"] == 500

    break_started = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/breaks",
        json={"planned_duration_seconds": 900, "started_at": "2026-09-05T18:25:00+07:00"},
    )
    assert break_started.status_code == 201
    break_id = break_started.json()["id"]
    assert break_started.json()["status"] == "running"

    second_drink = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/drinks",
        json={
            "category": "beer",
            "name": f"Test Beer {suffix}",
            "volume_ml": 330,
            "abv_percent": 5,
            "logged_at": "2026-09-05T18:30:00+07:00",
        },
    )
    assert second_drink.status_code == 201

    session_after_break = client.get(f"/api/v1/alcohol/sessions/{session_id}")
    assert session_after_break.status_code == 200
    break_state = next(item for item in session_after_break.json()["breaks"] if item["id"] == break_id)
    assert break_state["status"] == "interrupted"
    assert break_state["interrupted_by_drink_id"] == second_drink.json()["id"]
    assert session_after_break.json()["drink_count"] == 2
    assert session_after_break.json()["total_water_ml"] == 500

    paused = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/pause",
        json={"at": "2026-09-05T18:40:00+07:00"},
    )
    assert paused.status_code == 200
    assert paused.json()["paused_at"] is not None

    # Logging a drink resumes the tracking session automatically.
    auto_resume = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/drinks",
        json={
            "category": "wine",
            "name": f"Test Wine {suffix}",
            "volume_ml": 150,
            "abv_percent": 13,
            "logged_at": "2026-09-05T18:50:00+07:00",
        },
    )
    assert auto_resume.status_code == 201
    resumed_state = client.get(f"/api/v1/alcohol/sessions/{session_id}").json()
    assert resumed_state["paused_at"] is None
    assert resumed_state["total_paused_seconds"] == 600

    edited_drink = client.patch(
        f"/api/v1/alcohol/drinks/{drink_id}",
        json={"abv_percent": 5.5},
    )
    assert edited_drink.status_code == 200
    assert edited_drink.json()["alcohol_grams"] == pytest.approx(14.321, abs=0.001)

    favorite = client.post(
        "/api/v1/alcohol/favorites",
        json={
            "category": "beer",
            "name": f"Favorite Beer {suffix}",
            "brand": "Pace Test",
            "volume_ml": 330,
            "abv_percent": 5,
        },
    )
    assert favorite.status_code == 201
    favorite_id = favorite.json()["id"]

    logged_favorite = client.post(
        f"/api/v1/alcohol/favorites/{favorite_id}/log",
        json={"session_id": session_id, "logged_at": "2026-09-05T19:00:00+07:00"},
    )
    assert logged_favorite.status_code == 201
    favorite_after = client.get(f"/api/v1/alcohol/favorites/{favorite_id}")
    assert favorite_after.status_code == 200
    assert favorite_after.json()["usage_count"] == 1

    completed = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/complete",
        json={"at": "2026-09-05T20:00:00+07:00"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    reopened = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/reopen",
        json={"at": "2026-09-05T20:15:00+07:00"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "active"
    assert reopened.json()["total_paused_seconds"] == 1500

    final_complete = client.post(
        f"/api/v1/alcohol/sessions/{session_id}/complete",
        json={"at": "2026-09-05T20:30:00+07:00"},
    )
    assert final_complete.status_code == 200

    historical = client.post(
        "/api/v1/alcohol/sessions",
        json={"entry_mode": "historical", "historical_date": "2026-09-01"},
    )
    assert historical.status_code == 201
    historical_id = historical.json()["id"]
    assert historical.json()["status"] == "completed"
    assert historical.json()["started_at"] is None

    historical_drink = client.post(
        f"/api/v1/alcohol/sessions/{historical_id}/drinks",
        json={
            "category": "spirits",
            "name": "Whisky",
            "volume_ml": 30,
            "abv_percent": 40,
        },
    )
    assert historical_drink.status_code == 201
    assert historical_drink.json()["logged_at"] is None

    listed = client.get("/api/v1/alcohol/sessions?from_date=2026-09-01&to_date=2026-09-05")
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert {session_id, historical_id}.issubset(ids)

    assert client.delete(f"/api/v1/alcohol/sessions/{historical_id}").status_code == 204
    assert client.delete(f"/api/v1/alcohol/sessions/{session_id}").status_code == 204
    assert client.delete(f"/api/v1/alcohol/favorites/{favorite_id}").status_code == 204
