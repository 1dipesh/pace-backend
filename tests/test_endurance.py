import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
def test_cardio_and_hybrid_vertical_slice() -> None:
    suffix = uuid.uuid4().hex[:8]

    cardio = client.post(
        "/api/v1/training/cardio/activities",
        json={
            "activity_type": "running",
            "name": f"Easy Run {suffix}",
            "activity_date": "2026-09-05",
            "duration_seconds": 1800,
            "distance_km": 5,
            "notes": "Comfortable effort",
        },
    )
    assert cardio.status_code == 201
    cardio_id = cardio.json()["id"]
    assert cardio.json()["pace_seconds_per_km"] == 360.0
    assert cardio.json()["average_speed_kmh"] == 10.0

    updated = client.patch(
        f"/api/v1/training/cardio/activities/{cardio_id}",
        json={"distance_km": 5.2},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2

    listed = client.get("/api/v1/training/cardio/activities?activity_type=running")
    assert listed.status_code == 200
    assert any(item["id"] == cardio_id for item in listed.json())

    hybrid = client.post(
        "/api/v1/training/hybrid/sessions",
        json={
            "session_type": "hyrox_full",
            "name": f"HYROX Full {suffix}",
            "started_at": "2026-09-05T10:00:00+07:00",
            "completed_at": "2026-09-05T11:20:00+07:00",
            "total_duration_seconds": 4800,
            "segments": [
                {
                    "position": 0,
                    "segment_type": "run",
                    "segment_name": "Run 1",
                    "target_distance_m": 1000,
                    "duration_seconds": 300,
                },
                {
                    "position": 1,
                    "segment_type": "station",
                    "segment_name": "SkiErg",
                    "station_key": "ski_erg",
                    "target_distance_m": 1000,
                    "duration_seconds": 260,
                },
            ],
        },
    )
    assert hybrid.status_code == 201
    hybrid_id = hybrid.json()["id"]
    assert len(hybrid.json()["segments"]) == 2
    assert hybrid.json()["segments"][1]["station_key"] == "ski_erg"

    replacement = client.put(
        f"/api/v1/training/hybrid/sessions/{hybrid_id}",
        json={
            "session_type": "hyrox_full",
            "name": f"HYROX Full Corrected {suffix}",
            "started_at": "2026-09-05T10:00:00+07:00",
            "completed_at": "2026-09-05T11:19:00+07:00",
            "total_duration_seconds": 4740,
            "segments": [
                {
                    "position": 0,
                    "segment_type": "run",
                    "segment_name": "Run 1",
                    "target_distance_m": 1000,
                    "duration_seconds": 295,
                }
            ],
        },
    )
    assert replacement.status_code == 200
    assert replacement.json()["version"] == 2
    assert len(replacement.json()["segments"]) == 1
    assert replacement.json()["segments"][0]["duration_seconds"] == 295

    fetched = client.get(f"/api/v1/training/hybrid/sessions/{hybrid_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == f"HYROX Full Corrected {suffix}"

    deleted_cardio = client.delete(f"/api/v1/training/cardio/activities/{cardio_id}")
    assert deleted_cardio.status_code == 204
    assert client.get(f"/api/v1/training/cardio/activities/{cardio_id}").status_code == 404

    deleted_hybrid = client.delete(f"/api/v1/training/hybrid/sessions/{hybrid_id}")
    assert deleted_hybrid.status_code == 204
    assert client.get(f"/api/v1/training/hybrid/sessions/{hybrid_id}").status_code == 404
