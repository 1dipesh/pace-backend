from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.auth import AuthIdentity
from app.db.session import SessionLocal
from app.models.nutrition import NutritionFood, NutritionEntry, NutritionSavedMealItem
from app.services.nutrition_sync_service import mapped_id
from tests.conftest import FakeTokenVerifier

URL = '/api/v1/sync/nutrition'
NOW = '2026-09-09T10:00:00.000Z'
FOOD = dict(id='nutrition-food_test', name='Rice', category='carb', basisAmount=100, basisUnit='g',
            nutrition=dict(calories=130, protein=2.7, carbs=28, fat=0.3), isStarter=False,
            preparation='Boiled', servingLabel='cooked rice', note='Keep this note', createdAt=NOW, updatedAt=NOW)
MEAL = dict(id='nutrition-meal_test', name='Lunch', items=[dict(foodId=FOOD['id'], amount=150)], createdAt=NOW, updatedAt=NOW)
ENTRY = dict(id='nutrition-entry_test', foodId=FOOD['id'], date='2026-09-09', amount=150, unit='g', foodName='Rice',
             nutrition=dict(calories=195, protein=4.05, carbs=42, fat=0.45), mealTemplateId=MEAL['id'], mealGroupId='group-1', mealName='Lunch',
             loggedAt=NOW, createdAt=NOW, updatedAt=NOW)

@pytest.fixture
def clients():
    clients = []
    for _ in range(2):
        token = str(uuid4())
        FakeTokenVerifier.identities[token] = AuthIdentity(subject=token, email=f'{token}@example.com')
        c = TestClient(app, headers={'Authorization': f'Bearer {token}'})
        clients.append(c)
    yield clients
    for c in clients: c.close()


def change(entity, data, version=0, cid=None):
    return dict(entity=entity, id=cid or data['id'], expected_version=version, data=data)


def mutation(*changes):
    return dict(mutation_id=str(uuid4()), changes=list(changes))


def send(c, *changes):
    result = c.put(URL, json=mutation(*changes))
    assert result.status_code == 200, result.text
    return result.json()['records']


def test_import_relations_snapshots_retry_and_isolation(clients):
    a, b = clients
    assert TestClient(app).get(URL).status_code == 401
    p = mutation(change('entries', ENTRY), change('meals', MEAL), change('foods', FOOD))
    saved = a.put(URL, json=p)
    assert saved.status_code == 200, saved.text
    assert a.put(URL, json=p).json() == saved.json()
    assert b.get(URL).json() == {'records': []}
    cloud = a.get(URL).json()['records']
    assert {r['entity']: r['data'] for r in cloud} == dict(foods=FOOD, entries=ENTRY, meals=MEAL)
    uid = a.get('/api/v1/auth/me').json()['id']
    from uuid import UUID
    uid = UUID(uid)
    with SessionLocal() as db:
        food = db.get(NutritionFood, mapped_id(uid, 'foods', FOOD['id']))
        entry = db.get(NutritionEntry, mapped_id(uid, 'entries', ENTRY['id']))
        item = db.scalar(select(NutritionSavedMealItem).where(NutritionSavedMealItem.user_id == uid))
        assert entry.source_food_id == item.food_id == food.id
        assert float(entry.calories_kcal_snapshot) == 195
    updated = deepcopy(FOOD)
    updated['nutrition']['calories'] = 200
    send(a, change('foods', updated, 1))
    assert a.put(URL, json=p).json() == saved.json()  # replay never reverts v2
    assert next(r for r in a.get(URL).json()['records'] if r['entity'] == 'entries')['data'] == ENTRY
    p['changes'][0]['data']['foodName'] = 'Tampered'
    assert a.put(URL, json=p).status_code == 409


def test_conflict_is_atomic_and_deletion_survives_stale_device(clients):
    a, _ = clients
    send(a, change('foods', FOOD), change('meals', MEAL), change('entries', ENTRY))
    response = a.put(URL, json=mutation(change('meals', None, 0, MEAL['id']), change('entries', None, 1, ENTRY['id'])))
    assert response.status_code == 409
    assert all(r['data'] for r in a.get(URL).json()['records'])
    send(a, change('meals', None, 1, MEAL['id']))
    # Diary snapshots remain valid even after deleting the template.
    assert next(r for r in a.get(URL).json()['records'] if r['entity'] == 'entries')['data'] == ENTRY
    send(a, change('entries', None, 1, ENTRY['id']))
    assert a.put(URL, json=mutation(change('entries', ENTRY, 1))).status_code == 409
    send(a, change('entries', ENTRY, 2))
    assert next(r for r in a.get(URL).json()['records'] if r['entity'] == 'entries')['version'] == 3


def test_validation_reference_ownership_and_optional_goals(clients):
    a, b = clients
    send(b, change('foods', FOOD))
    assert a.put(URL, json=mutation(change('entries', ENTRY))).status_code == 422
    for field, value in [('basisAmount', -1), ('name', 'x'*161), ('category', 'unknown')]:
        invalid = {**FOOD, field: value}
        assert a.put(URL, json=mutation(change('foods', invalid))).status_code == 422
    invalid = {**FOOD, 'nutrition': {**FOOD['nutrition'], 'protein': 'NaN'}}
    assert a.put(URL, json=mutation(change('foods', invalid))).status_code == 422
    assert a.put(URL, json=mutation(change('foods', FOOD), change('foods', FOOD))).status_code == 422
    goals = dict(id='default', protein=120, updatedAt=NOW)
    send(a, change('goals', goals))
    assert a.get(URL).json()['records'][0]['data'] == goals
    goals.update(calories=2200, carbs=250, fat=70)
    send(a, change('goals', goals, 1))
    send(a, change('foods', FOOD), change('entries', ENTRY))
    assert a.put(URL, json=mutation(change('foods', None, 1, FOOD['id']))).status_code == 422


def test_legacy_data_imported_and_old_writes_blocked(clients):
    a, _ = clients
    f = a.post('/api/v1/nutrition/foods', json=dict(name='Legacy rice', basis_amount=100, basis_unit='g', calories_kcal=130,
        protein_g=2.7, carbs_g=28, fat_g=0.3))
    assert f.status_code == 201, f.text
    first = a.get(URL)
    assert first.status_code == 200, first.text
    food = first.json()['records'][0]
    assert food['id'] == f.json()['id']
    assert food['data']['nutrition']['calories'] == 130
    assert a.get(URL).json() == first.json()
    assert a.delete(f"/api/v1/nutrition/foods/{food['id']}").status_code == 409
    food['data']['name'] = 'Changed through sync'
    send(a, change('foods', food['data'], food['version']))
    assert a.get(f"/api/v1/nutrition/foods/{food['id']}").json()['name'] == 'Changed through sync'


def test_legacy_manual_snapshot_and_deleted_food_links_survive_import(clients):
    a, _ = clients
    f = a.post('/api/v1/nutrition/foods', json=dict(name='Old food', basis_amount=100, basis_unit='g', calories_kcal=100,
        protein_g=10, carbs_g=10, fat_g=1)).json()
    entry = a.post('/api/v1/nutrition/entries', json=dict(logged_date='2026-09-08', meal_type='lunch', food_id=f['id'], amount=150, unit='g'))
    assert entry.status_code == 201, entry.text
    manual = a.post('/api/v1/nutrition/entries', json=dict(logged_date='2026-09-08', meal_type='snack', manual=dict(name='Manual snack', amount=1, unit='serving', calories_kcal=50, protein_g=1, carbs_g=10, fat_g=1)))
    assert manual.status_code == 201, manual.text
    assert a.delete(f"/api/v1/nutrition/foods/{f['id']}").status_code == 204
    result = a.get(URL)
    assert result.status_code == 200, result.text
    rows = {(r['entity'], r['id']): r for r in result.json()['records']}
    assert rows[('foods', f['id'])]['data'] is None
    for eid in (entry.json()['id'], manual.json()['id']):
        data = rows[('entries', eid)]['data']
        archived = rows[('foods', data['foodId'])]['data']
        assert archived['isLibraryItem'] is False
        assert data['nutrition']['calories'] in (150, 50)
    # The complete graph is valid for subsequent mutations.
    send(a, change('goals', dict(id='default', protein=100, updatedAt=NOW)))


def test_numeric_bounds_and_cross_account_uuid_collision(clients):
    a, b = clients
    fid = str(uuid4())
    send(a, change('foods', {**FOOD, 'id': fid}))
    assert b.put(URL, json=mutation(change('foods', {**FOOD, 'id': fid}))).status_code == 422
    assert b.get(URL).json() == {'records': []}
    assert a.put(URL, json=mutation(change('foods', {**FOOD, 'basisAmount': 0.001}))).status_code == 422
    assert a.put(URL, json=mutation(change('goals', dict(id='default', calories=999999, updatedAt=NOW)))).status_code == 422
