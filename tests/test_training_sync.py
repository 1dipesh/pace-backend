from copy import deepcopy
from uuid import uuid4, UUID
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.db.session import SessionLocal
from app.models.training import TrainingSet, TrainingSession, TrainingSessionExercise
from app.models.endurance import HybridSegment
from app.services.training_sync_service import mapped_id
from tests.test_nutrition_sync import clients  # noqa: F401

URL='/api/v1/sync/training'
NOW='2026-09-09T10:00:00.000Z'
END='2026-09-09T11:00:00.000Z'
EX=dict(id='exercise-a',name='Squat',primaryMuscle='quads',secondaryMuscles=['glutes'],equipment='barbell',trackingMode='weight_reps',isStarter=False,isFavorite=True,notes='Controlled',createdAt=NOW,updatedAt=NOW)
TPL=dict(id='template-a',name='Leg day',items=[dict(exerciseId=EX['id'],order=0,targetSets=3,warmupSets=1,restSeconds=90)],createdAt=NOW,updatedAt=NOW)
SESSION=dict(id='session-a',name='Leg day',status='completed',date='2026-09-09',templateId=TPL['id'],startedAt=NOW,endedAt=END,createdAt=NOW,updatedAt=END)
LOG=dict(id='log-a',sessionId=SESSION['id'],exerciseId=EX['id'],exerciseName='Squat snapshot',order=0,trackingMode='weight_reps',primaryMuscle='quads',equipment='barbell',notes='Log note',createdAt=NOW,updatedAt=END)
SET=dict(id='set-a',sessionId=SESSION['id'],exerciseLogId=LOG['id'],exerciseId=EX['id'],setNumber=1,setType='working',weight=100,weightUnit='lb',reps=8,effortMode='rir',effortValue=2,restSeconds=90,completedAt=END,createdAt=NOW,updatedAt=END)
WORK=dict(id=SESSION['id'],session=SESSION,exercises=[dict(log=LOG,sets=[SET])])
ACT=dict(id='activity-a',name='Morning run',type='running',date='2026-09-09',durationSeconds=1800,distanceKm=5.25,notes='Easy',createdAt=NOW,updatedAt=END)
HYB=dict(id='hybrid-a',name='HYROX',status='completed',preset='hyrox_stations',date='2026-09-09',startedAt=NOW,endedAt=END,createdAt=NOW,updatedAt=END,segments=[dict(id='segment-a',order=0,kind='station',label='Sled push',stationType='sled_push',targetDistanceMeters=50,loadKg=100,startedAt=NOW,completedAt=END,durationSeconds=3600)])

def change(entity,data,version=0,cid=None):return dict(entity=entity,id=cid or data['id'],expected_version=version,data=data)
def mutation(*cs):return dict(mutation_id=str(uuid4()),changes=list(cs))
def send(c,*cs):
    r=c.put(URL,json=mutation(*cs)); assert r.status_code==200,r.text
    return r.json()['records']

def test_completed_workouts_project_atomically_and_replay_without_duplicates(clients):
    a,b=clients
    assert TestClient(app).get(URL).status_code==401
    p=mutation(change('workouts',WORK),change('templates',TPL),change('exercises',EX),change('activities',ACT),change('hybrid',HYB))
    r=a.put(URL,json=p); assert r.status_code==200,r.text
    assert a.put(URL,json=p).json()==r.json()
    assert b.get(URL).json()=={'records':[]}
    assert {x['entity']:x['data'] for x in a.get(URL).json()['records']}==dict(workouts=WORK,templates=TPL,exercises=EX,activities=ACT,hybrid=HYB)
    uid=UUID(a.get('/api/v1/auth/me').json()['id'])
    with SessionLocal() as db:
        session=db.get(TrainingSession,mapped_id(uid,'workouts',SESSION['id']))
        log=db.scalar(select(TrainingSessionExercise).where(TrainingSessionExercise.session_id==session.id,TrainingSessionExercise.deleted_at.is_(None)))
        sets=db.scalars(select(TrainingSet).where(TrainingSet.session_exercise_id==log.id,TrainingSet.deleted_at.is_(None))).all()
        assert len(sets)==1 and sets[0].weight_unit=='lb' and float(sets[0].weight)==100 and float(sets[0].rir)==2
        split=db.scalar(select(HybridSegment).where(HybridSegment.user_id==uid))
        assert float(split.load)==100 and split.station_key=='sled_push'
    newer=deepcopy(WORK);newer['exercises'][0]['sets'][0]['reps']=9
    send(a,change('workouts',newer,1))
    assert a.put(URL,json=p).json()==r.json()
    assert next(x for x in a.get(URL).json()['records'] if x['entity']=='workouts')['data']==newer
    assert a.put(URL,json=mutation(change('workouts',WORK,1))).status_code==409


def test_deletion_cascades_sets_and_stale_device_cannot_restore(clients):
    a,_=clients
    send(a,change('exercises',EX),change('templates',TPL),change('workouts',WORK))
    send(a,change('templates',None,1,TPL['id']))
    assert next(x for x in a.get(URL).json()['records'] if x['entity']=='workouts')['data']==WORK
    send(a,change('workouts',None,1,WORK['id']))
    assert a.put(URL,json=mutation(change('workouts',WORK,1))).status_code==409
    uid=UUID(a.get('/api/v1/auth/me').json()['id'])
    with SessionLocal() as db:
        assert not db.scalars(select(TrainingSet).where(TrainingSet.user_id==uid,TrainingSet.deleted_at.is_(None))).all()
    send(a,change('workouts',WORK,2))


def test_invalid_payloads_and_cross_account_references_are_rejected(clients):
    a,b=clients
    send(b,change('exercises',EX))
    assert a.put(URL,json=mutation(change('templates',TPL))).status_code==422
    bad=deepcopy(WORK);bad['session']['status']='active'
    assert a.put(URL,json=mutation(change('workouts',bad))).status_code==422
    bad=deepcopy(WORK);bad['exercises'][0]['sets'][0]['sessionId']='someone-else'
    assert a.put(URL,json=mutation(change('workouts',bad))).status_code==422
    bad=deepcopy(WORK);bad['exercises'][0]['sets'][0]['effortMode']='rpe';bad['exercises'][0]['sets'][0]['effortValue']=0
    assert a.put(URL,json=mutation(change('workouts',bad))).status_code==422
    bad=deepcopy(HYB);bad['segments'].append(bad['segments'][0])
    assert a.put(URL,json=mutation(change('hybrid',bad))).status_code==422
    assert a.put(URL,json=mutation(change('activities',{**ACT,'durationSeconds':-1}))).status_code==422
    assert a.get(URL).json()=={'records':[]}


def test_legacy_exercises_import_and_legacy_writes_stop_after_sync(clients):
    a,_=clients
    ex=a.post('/api/v1/training/exercises',json=dict(name='Bench',exercise_type='weighted',primary_muscle='chest',equipment='barbell'))
    assert ex.status_code==201,ex.text
    cloud=a.get(URL);assert cloud.status_code==200,cloud.text
    row=cloud.json()['records'][0]
    assert row['id']==ex.json()['id'] and row['data']['trackingMode']=='weight_reps'
    assert a.delete('/api/v1/training/exercises/'+row['id']).status_code==409
    assert a.get('/api/v1/training/exercises/'+row['id']).status_code==200
    changed={**row['data'],'name':'Updated bench'}
    send(a,change('exercises',changed,row['version']))
    assert a.get('/api/v1/training/exercises/'+row['id']).json()['name']=='Updated bench'


def test_legacy_active_session_can_finish_before_enabling_sync(clients):
    a,_=clients
    created=a.post('/api/v1/training/sessions',json=dict(name='Legacy active',started_at=NOW,exercises=[]))
    assert created.status_code==201,created.text
    sid=created.json()['id']
    blocked=a.get(URL)
    assert blocked.status_code==409 and blocked.json()['detail']['code']=='legacy_active_training'
    finished=a.patch('/api/v1/training/sessions/'+sid,json={'completed_at':END})
    assert finished.status_code==200,finished.text
    cloud=a.get(URL)
    assert cloud.status_code==200,cloud.text
    record=next(r for r in cloud.json()['records'] if r['entity']=='workouts')
    assert record['data']['session']['status']=='completed'
    assert record['data']['session']['id']==sid


def test_optional_effort_and_bounds_preserve_legacy_read_compatibility(clients):
    a,_=clients
    work=deepcopy(WORK);del work['exercises'][0]['sets'][0]['effortValue']
    send(a,change('exercises',EX),change('workouts',work),change('activities',ACT),change('hybrid',HYB))
    uid=UUID(a.get('/api/v1/auth/me').json()['id'])
    for route,entity,cid in [('sessions','workouts',WORK['id']),('cardio/activities','activities',ACT['id']),('hybrid/sessions','hybrid',HYB['id'])]:
        response=a.get(f'/api/v1/training/{route}/{mapped_id(uid,entity,cid)}')
        assert response.status_code==200,response.text
    bad=deepcopy(WORK);bad['exercises'][0]['sets'][0]['reps']=1001
    assert a.put(URL,json=mutation(change('workouts',bad,1))).status_code==422
    assert a.put(URL,json=mutation(change('activities',{**ACT,'distanceKm':10001},1))).status_code==422
