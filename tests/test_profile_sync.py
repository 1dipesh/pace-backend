from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
A = {'Authorization': 'Bearer user-a-token'}
B = {'Authorization': 'Bearer user-b-token'}
PROFILE = dict(date_of_birth='1990-12-20', height_cm=178, weight_kg=78,
               calorie_estimate_sex='male', goal='build_muscle', activity_level='active',
               training_experience='intermediate', training_days_per_week=4)
URL = '/api/v1/sync/profile'


def mutation(version, **fields):
    return dict(mutation_id=str(uuid4()), expected_version=version, profile={**PROFILE, **fields})


def test_sync_retry_conflict_and_account_isolation():
    assert client.get(URL).status_code == 401
    assert client.put(URL, json=mutation(0)).status_code == 401
    a_before = client.get(URL, headers=A).json()
    b_before = client.get(URL, headers=B).json()
    first = mutation(a_before['version'])
    response = client.put(URL, headers=A, json=first)
    assert response.status_code == 200
    saved = response.json()
    assert client.put(URL, headers=A, json=first).json() == saved
    assert client.get(URL, headers=B).json() == b_before
    # A second device cannot overwrite a version it has not seen.
    stale = client.put(URL, headers=A, json=mutation(a_before['version'], weight_kg=90))
    assert stale.status_code == 409
    assert stale.json()['detail']['current'] == saved
    latest = client.put(URL, headers=A, json=mutation(saved['version'], weight_kg=80)).json()
    assert latest['version'] == saved['version'] + 1
    # Late replay returns the original receipt without reverting newer data.
    assert client.put(URL, headers=A, json=first).json() == saved
    assert client.get(URL, headers=A).json() == latest
    first['profile']['weight_kg'] = 100
    assert client.put(URL, headers=A, json=first).status_code == 409
    assert client.get(URL, headers=A).json() == latest


def test_deletion_tombstone_requires_current_version_to_restore():
    before = client.get(URL, headers=A).json()
    if not before['profile']:
        before = client.put(URL, headers=A, json=mutation(before['version'])).json()
    assert client.delete('/api/v1/profile', headers=A).status_code == 204
    deleted = client.get(URL, headers=A).json()
    assert deleted['deleted'] is True
    assert deleted['profile'] is None
    assert deleted['version'] > before['version']
    assert client.put(URL, headers=A, json=mutation(before['version'])).status_code == 409
    restored = client.put(URL, headers=A, json=mutation(deleted['version'])).json()
    assert restored['profile']['weight_kg'] == 78
    assert restored['version'] == deleted['version'] + 1


def test_profile_sync_validation():
    version = client.get(URL, headers=A).json()['version']
    for changes in [dict(weight_kg=-1), dict(goal='fat_loss'), dict(date_of_birth='2025-01-01')]:
        assert client.put(URL, headers=A, json=mutation(version, **changes)).status_code == 422
    assert client.get(URL, headers=A).json()['version'] == version
