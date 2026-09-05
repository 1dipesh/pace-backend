import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_strength_training_vertical_slice() -> None:
    suffix = uuid.uuid4().hex[:8]

    settings = client.put(
        "/api/v1/training/settings",
        json={
            "default_warmup_rest_seconds": 60,
            "default_working_rest_seconds": 150,
            "effort_mode": "rir",
        },
    )
    assert settings.status_code == 200
    assert settings.json()["default_working_rest_seconds"] == 150

    exercise = client.post(
        "/api/v1/training/exercises",
        json={
            "name": f"Barbell Row {suffix}",
            "exercise_type": "weighted",
            "primary_muscle": "Back",
            "equipment": "Barbell",
            "is_favorite": True,
        },
    )
    assert exercise.status_code == 201
    exercise_id = exercise.json()["id"]

    template = client.post(
        "/api/v1/training/templates",
        json={
            "name": f"Pull Day {suffix}",
            "source_program_name": "Pace Test Program",
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "position": 0,
                    "sets": [
                        {
                            "position": 0,
                            "set_type": "warmup",
                            "target_reps": 10,
                            "target_weight": 20,
                            "weight_unit": "kg",
                        },
                        {
                            "position": 1,
                            "set_type": "working",
                            "target_reps": 8,
                            "target_weight": 60,
                            "weight_unit": "kg",
                        },
                    ],
                }
            ],
        },
    )
    assert template.status_code == 201
    template_id = template.json()["id"]
    assert template.json()["exercises"][0]["sets"][0]["set_type"] == "warmup"

    renamed = client.patch(
        f"/api/v1/training/exercises/{exercise_id}",
        json={"name": f"Pendlay Row {suffix}"},
    )
    assert renamed.status_code == 200

    template_after_rename = client.get(f"/api/v1/training/templates/{template_id}")
    assert template_after_rename.status_code == 200
    assert template_after_rename.json()["exercises"][0]["exercise_name"] == f"Pendlay Row {suffix}"

    session = client.post(
        "/api/v1/training/sessions",
        json={
            "template_id": template_id,
            "name": f"Pull Session {suffix}",
            "started_at": "2026-09-05T10:00:00+07:00",
            "completed_at": "2026-09-05T11:00:00+07:00",
            "exercises": [
                {
                    "exercise_id": exercise_id,
                    "position": 0,
                    "sets": [
                        {
                            "position": 0,
                            "set_type": "warmup",
                            "weight": 20,
                            "weight_unit": "kg",
                            "reps": 10,
                            "effort_mode": "off",
                            "rest_seconds": 60,
                        },
                        {
                            "position": 1,
                            "set_type": "working",
                            "weight": 60,
                            "weight_unit": "kg",
                            "reps": 8,
                            "effort_mode": "rir",
                            "rir": 2,
                            "rest_seconds": 150,
                        },
                    ],
                }
            ],
        },
    )
    assert session.status_code == 201
    session_id = session.json()["id"]
    assert session.json()["exercises"][0]["exercise_name_snapshot"] == f"Pendlay Row {suffix}"
    assert session.json()["exercises"][0]["sets"][0]["set_type"] == "warmup"
    assert session.json()["exercises"][0]["sets"][1]["set_type"] == "working"

    renamed_again = client.patch(
        f"/api/v1/training/exercises/{exercise_id}",
        json={"name": f"Barbell Row Updated {suffix}"},
    )
    assert renamed_again.status_code == 200

    historical = client.get(f"/api/v1/training/sessions/{session_id}")
    assert historical.status_code == 200
    assert historical.json()["exercises"][0]["exercise_name_snapshot"] == f"Pendlay Row {suffix}"

    sessions = client.get("/api/v1/training/sessions")
    assert sessions.status_code == 200
    assert any(item["id"] == session_id for item in sessions.json())

    deleted = client.delete(f"/api/v1/training/sessions/{session_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/v1/training/sessions/{session_id}")
    assert missing.status_code == 404
