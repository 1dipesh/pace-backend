from copy import deepcopy
from uuid import uuid4, UUID
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models.alcohol import AlcoholSession, AlcoholDrink, AlcoholWaterEntry, AlcoholBreak
from app.services.alcohol_sync_service import mapped_id
from app.schemas.alcohol_sync import Bundle
from tests.test_nutrition_sync import clients  # noqa: F401

URL='/api/v1/sync/alcohol'
NOW='2026-09-10T10:00:00.000Z'
END='2026-09-10T11:00:00.000Z'
SESSION=dict(id='session-a',startedAt=NOW,endedAt=END,status='ended',entryMode='live',totalPausedMs=1234,createdAt=NOW,updatedAt=END)
DRINK=dict(id='drink-a',sessionId='session-a',category='spirit',name='Whisky',volumeMl=30,abv=40,alcoholMl=12,alcoholGrams=9.468,consumedAt=NOW,createdAt=NOW,updatedAt=NOW)
WATER=dict(id='water-a',sessionId='session-a',volumeMl=250,container='cup',loggedAt=NOW,createdAt=NOW)
BREAK=dict(id='break-a',sessionId='session-a',startedAt=NOW,plannedEndAt=END,endedAt=END,plannedMinutes=60,status='completed',trigger='paceSuggestion',createdAt=NOW,updatedAt=END)
BUNDLE=dict(id='session-a',session=SESSION,drinks=[DRINK],water=[WATER],breaks=[BREAK])
FAV=dict(id='favorite-a',category='beer',name='Beer',volumeMl=330,abv=5,usageCount=2,lastUsedAt=NOW,createdAt=NOW,updatedAt=NOW)
PROFILE=dict(id='default',ageConfirmed=True,weightKg=70,onboardingCompleted=True)

def change(entity,data,version=0,cid=None): return dict(entity=entity,id=cid or data['id'],expected_version=version,data=data)
def mutation(*cs): return dict(mutation_id=str(uuid4()),changes=list(cs))
def send(c,*cs):
    r=c.put(URL,json=mutation(*cs)); assert r.status_code==200,r.text
    return r.json()['records']

def test_atomic_projection_idempotence_and_account_isolation(clients):
    a,b=clients
    assert TestClient(app).get(URL).status_code==401
    p=mutation(change('sessions',BUNDLE),change('favorites',FAV),change('profile',PROFILE))
    r=a.put(URL,json=p);assert r.status_code==200,r.text
    assert 'no-store' in r.headers['cache-control']
    assert a.put(URL,json=p).json()==r.json()
    assert b.get(URL).json()=={'records':[]}
    assert {r['entity']:r['data'] for r in a.get(URL).json()['records']}==dict(sessions=BUNDLE,favorites=FAV,profile=PROFILE)
    uid=UUID(a.get('/api/v1/auth/me').json()['id'])
    old=a.get(f'/api/v1/alcohol/sessions/{mapped_id(uid,"sessions","session-a")}')
    assert old.status_code==200,old.text
    assert old.json()['drinks'][0]['category']=='spirits'
    assert old.json()['total_water_ml']==250
    assert old.json()['breaks'][0]['planned_duration_seconds']==3600
    with SessionLocal() as db:
        assert len(db.scalars(select(AlcoholDrink).where(AlcoholDrink.user_id==uid)).all())==1
    newer=deepcopy(BUNDLE);newer['drinks'][0]['name']='Updated name'
    send(a,change('sessions',newer,1))
    assert a.put(URL,json=p).json()==r.json()
    assert next(x for x in a.get(URL).json()['records'] if x['entity']=='sessions')['data']==newer
    p['changes'][0]['data']=newer
    assert a.put(URL,json=p).json()['detail']['code']=='mutation_id_reused'

def test_stale_batch_does_not_partially_commit_and_deletion_cascades(clients):
    a,_=clients
    send(a,change('sessions',BUNDLE),change('favorites',FAV))
    send(a,change('sessions',None,1,'session-a'))
    stale=a.put(URL,json=mutation(change('sessions',BUNDLE,1),change('favorites',{**FAV,'name':'Should not save'},1)))
    assert stale.status_code==409
    assert next(x for x in a.get(URL).json()['records'] if x['entity']=='favorites')['data']==FAV
    uid=UUID(a.get('/api/v1/auth/me').json()['id'])
    with SessionLocal() as db:
        for model in [AlcoholSession,AlcoholDrink,AlcoholWaterEntry,AlcoholBreak]:
            assert not db.scalars(select(model).where(model.user_id==uid,model.deleted_at.is_(None))).all()
    send(a,change('sessions',BUNDLE,2))

def test_backdated_date_and_placeholder_times_round_trip_without_live_timing(clients):
    a,_=clients
    data=deepcopy(BUNDLE);data['session'].update(entryMode='backdated',historicalDate='2026-09-08',endedAt=NOW)
    send(a,change('sessions',data))
    uid=UUID(a.get('/api/v1/auth/me').json()['id'])
    old=a.get(f'/api/v1/alcohol/sessions/{mapped_id(uid,"sessions","session-a")}').json()
    assert old['entry_mode']=='historical' and old['session_date']=='2026-09-08'
    assert old['started_at'] is None and old['drinks'][0]['logged_at'] is None
    assert a.get(URL).json()['records'][0]['data']==data

def test_active_invalid_links_quantities_and_duplicate_children_rejected(clients):
    a,_=clients
    invalid=[]
    d=deepcopy(BUNDLE);d['drinks'][0]['volumeMl']='30';invalid.append(d)
    d=deepcopy(BUNDLE);d['session']['status']='active';invalid.append(d)
    d=deepcopy(BUNDLE);d['drinks'][0]['sessionId']='wrong';invalid.append(d)
    d=deepcopy(BUNDLE);d['drinks'][0]['alcoholGrams']=200;invalid.append(d)
    d=deepcopy(BUNDLE);d['drinks'].append(d['drinks'][0]);invalid.append(d)
    d=deepcopy(BUNDLE);d['session']['endedAt']='2026-09-01T00:00:00Z';invalid.append(d)
    for d in invalid: assert a.put(URL,json=mutation(change('sessions',d))).status_code==422
    assert a.put(URL,json=mutation(change('profile',{**PROFILE,'ageConfirmed':False}))).status_code==422
    other=deepcopy(BUNDLE);other['id']='session-b';other['session']['id']='session-b'
    for kind in ('drinks','water','breaks'):
        for c in other[kind]:c['sessionId']='session-b'
    assert a.put(URL,json=mutation(change('sessions',BUNDLE),change('sessions',other))).status_code==422
    assert a.get(URL).json()=={'records':[]}

def test_legacy_bootstrap_and_legacy_write_guard(clients):
    a,_=clients
    r=a.post('/api/v1/alcohol/sessions',json={'entry_mode':'historical','historical_date':'2026-09-08','notes':'Legacy note'})
    assert r.status_code==201,r.text
    sid=r.json()['id']
    drink=a.post(f'/api/v1/alcohol/sessions/{sid}/drinks',json=dict(category='beer',name='Legacy beer',volume_ml=330,abv_percent=5))
    assert drink.status_code==201,drink.text
    cloud=a.get(URL);assert cloud.status_code==200,cloud.text
    data=cloud.json()['records'][0]['data'];Bundle.model_validate(data)
    assert data['session']['notes']=='Legacy note'
    assert data['id']==sid and data['session']['historicalDate']=='2026-09-08'
    assert data['drinks'][0]['id']==drink.json()['id']
    assert a.delete(f'/api/v1/alcohol/sessions/{sid}').status_code==409
    assert a.get(f'/api/v1/alcohol/sessions/{sid}').status_code==200
    send(a,change('sessions',data,cloud.json()['records'][0]['version']))

def test_legacy_active_session_not_stranded_by_bootstrap(clients):
    a,_=clients
    r=a.post('/api/v1/alcohol/sessions',json={'entry_mode':'live','started_at':NOW})
    assert r.status_code==201,r.text
    sid=r.json()['id']
    assert a.get(URL).json()['detail']['code']=='legacy_active_alcohol'
    r=a.post(f'/api/v1/alcohol/sessions/{sid}/complete',json={'at':END})
    assert r.status_code==200,r.text
    assert a.get(URL).status_code==200

def test_cross_account_uuid_collision_rolls_back_all_changes(clients):
    a,b=clients
    fid=str(uuid4())
    send(b,change('favorites',{**FAV,'id':fid}))
    r=a.put(URL,json=mutation(change('profile',PROFILE),change('favorites',{**FAV,'id':fid})))
    assert r.status_code==422,r.text
    assert a.get(URL).json()=={'records':[]}
