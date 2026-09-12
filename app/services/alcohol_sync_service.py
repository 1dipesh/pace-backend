"""Atomic completed-session sync with projections for the existing Alcohol reads."""
from datetime import datetime, timezone, date, timedelta
from uuid import UUID, uuid5
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.models.alcohol_sync import AlcoholSyncRecord as Row
from app.models.alcohol import AlcoholSession, AlcoholDrink, AlcoholWaterEntry, AlcoholBreak, AlcoholFavorite
from app.services.nutrition_sync_service import lock, iso

CHILDREN={'drinks':AlcoholDrink,'water':AlcoholWaterEntry,'breaks':AlcoholBreak}


def legacy_guard(request:Request,db:Session=Depends(get_db),user:PaceUser=Depends(get_current_user)):
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        lock(db,user.id)
        if db.get(Row,(user.id,'meta','initialized')):
            raise HTTPException(409,detail={'code':'alcohol_sync_required','message':'Use /api/v1/sync/alcohol for Alcohol writes.'})


def mapped_id(uid,entity,cid):
    try: return UUID(cid)
    except ValueError: return uuid5(uid,f'alcohol:{entity}:{cid}')


def time(value): return datetime.fromisoformat(value.replace('Z','+00:00')) if value else None

def envelope(row): return dict(entity=row.entity,id=row.client_id,version=row.version,data=row.data)

def compact(data): return {k:v for k,v in data.items() if v is not None}

def owned(db,model,uid,oid,parent=None):
    obj=db.get(model,oid)
    if obj and (obj.user_id!=uid or (parent is not None and obj.session_id!=parent)):
        raise HTTPException(422,detail={'code':'record_id_collision'})
    return obj

def children(db,model,uid,sid):
    return db.scalars(select(model).where(model.user_id==uid,model.session_id==sid)).all()

def stamp(obj,data,version):
    obj.deleted_at=None; obj.version=version
    obj.created_at=time(data['createdAt']); obj.client_updated_at=time(data.get('updatedAt') or data['createdAt'])

def drink_fields(obj,data):
    obj.category='spirits' if data['category']=='spirit' else data['category']
    obj.name=data.get('name') or data.get('brand') or data['category'].capitalize()
    obj.brand=data.get('brand'); obj.volume_ml=data['volumeMl']; obj.abv_percent=data['abv']


def project(db,uid,entity,cid,data,version):
    # Alcohol eligibility/weight are intentionally separate from general Pace profile.
    if entity=='profile': return
    model=AlcoholSession if entity=='sessions' else AlcoholFavorite
    oid=mapped_id(uid,entity,cid)
    obj=owned(db,model,uid,oid)
    if data is None:
        if obj:
            obj.deleted_at=datetime.now(timezone.utc);obj.version=version
            if entity=='sessions':
                for child_model in CHILDREN.values():
                    for child in children(db,child_model,uid,oid): child.deleted_at=obj.deleted_at;child.version=version
        db.flush();return
    if not obj: obj=model(id=oid,user_id=uid);db.add(obj)
    root=data['session'] if entity=='sessions' else data
    stamp(obj,root,version)
    if entity=='favorites':
        drink_fields(obj,data);obj.usage_count=data['usageCount'];obj.last_used_at=time(data.get('lastUsedAt'))
        db.flush();return
    historical=root.get('entryMode')=='backdated'
    obj.entry_mode='historical' if historical else 'live';obj.status='completed'
    obj.session_date=date.fromisoformat(root['historicalDate']) if historical else time(root['startedAt']).date()
    obj.started_at=None if historical else time(root['startedAt']);obj.ended_at=None if historical else time(root['endedAt'])
    obj.notes=root.get('notes');obj.paused_at=None;obj.total_paused_seconds=root.get('totalPausedMs',0)//1000
    db.flush()
    for kind,child_model in CHILDREN.items():
        for old in children(db,child_model,uid,oid): old.deleted_at=datetime.now(timezone.utc);old.version=version
        for item in data[kind]:
            iid=mapped_id(uid,kind,item['id'])
            child=owned(db,child_model,uid,iid,oid)
            if not child: child=child_model(id=iid,user_id=uid,session_id=oid);db.add(child)
            stamp(child,item,version)
            if kind=='drinks':
                drink_fields(child,item);child.alcohol_grams=item['volumeMl']*item['abv']/100*0.789
                child.logged_at=None if historical else time(item['consumedAt'])
            elif kind=='water':
                child.volume_ml=max(1,round(item['volumeMl'])) if item.get('volumeMl') is not None else None
                child.container=item.get('containerLabel') or item.get('container');child.logged_at=None if historical else time(item['loggedAt'])
            else:
                child.started_at=time(item['startedAt']);child.ended_at=time(item.get('endedAt'))
                child.planned_duration_seconds=max(1,round(item['plannedMinutes']*60))
                # Preserve the recorded status, even for an old ended session whose break
                # was never explicitly settled. Sync must not invent a user action.
                child.status='running' if item['status']=='active' else item['status']
                interrupted=item.get('interruptedByDrinkId')
                target=owned(db,AlcoholDrink,uid,mapped_id(uid,'drinks',interrupted),oid) if interrupted else None
                child.interrupted_by_drink_id=target.id if target else None
            db.flush()


def base(obj): return dict(id=str(obj.id),createdAt=iso(obj.created_at),updatedAt=iso(obj.client_updated_at or obj.updated_at))

def common_drink(obj):
    return compact(dict(category='spirit' if obj.category=='spirits' else obj.category,name=obj.name,brand=obj.brand,volumeMl=float(obj.volume_ml),abv=float(obj.abv_percent)))


def bootstrap(db,uid):
    if db.get(Row,(uid,'meta','initialized')): return
    if db.scalar(select(AlcoholSession.id).where(AlcoholSession.user_id==uid,AlcoholSession.status=='active',AlcoholSession.deleted_at.is_(None)).limit(1)):
        raise HTTPException(409,detail={'code':'legacy_active_alcohol','message':'Finish or discard the active session created through the older API before enabling Alcohol sync.'})
    for obj in db.scalars(select(AlcoholFavorite).where(AlcoholFavorite.user_id==uid)).all():
        data=compact(dict(**base(obj),**common_drink(obj),usageCount=obj.usage_count,lastUsedAt=iso(obj.last_used_at) if obj.last_used_at else None))
        db.add(Row(user_id=uid,entity='favorites',client_id=str(obj.id),version=obj.version,data=None if obj.deleted_at else data))
    for obj in db.scalars(select(AlcoholSession).where(AlcoholSession.user_id==uid)).all():
        cid=str(obj.id)
        historical=obj.entry_mode=='historical'
        start=obj.started_at or datetime.combine(obj.session_date,datetime.min.time(),tzinfo=timezone.utc)+timedelta(hours=12)
        session=compact(dict(**base(obj),startedAt=iso(start),endedAt=iso(obj.ended_at or start),status='ended',entryMode='backdated' if historical else 'live',historicalDate=obj.session_date.isoformat() if historical else None,totalPausedMs=obj.total_paused_seconds*1000,notes=obj.notes))
        data=dict(id=cid,session=session,drinks=[],water=[],breaks=[])
        for kind,model in CHILDREN.items():
            for child in children(db,model,uid,obj.id):
                if child.deleted_at: continue
                d=dict(**base(child),sessionId=cid)
                if kind=='drinks':
                    ml=float(child.volume_ml)*float(child.abv_percent)/100
                    d.update(**common_drink(child),alcoholMl=ml,alcoholGrams=ml*0.789,consumedAt=iso(child.logged_at or start))
                elif kind=='water':
                    del d['updatedAt']
                    d.update(volumeMl=child.volume_ml,container=child.container if child.container in {'cup','bottle','custom'} else 'custom' if child.container else None,loggedAt=iso(child.logged_at or start),containerLabel=child.container if child.container not in {None,'cup','bottle','custom'} else None)
                else:
                    d.update(startedAt=iso(child.started_at),plannedEndAt=iso(child.started_at+timedelta(seconds=child.planned_duration_seconds)),endedAt=iso(child.ended_at) if child.ended_at else None,plannedMinutes=child.planned_duration_seconds/60,status='active' if child.status=='running' else child.status,trigger='manual',interruptedByDrinkId=str(child.interrupted_by_drink_id) if child.interrupted_by_drink_id else None)
                data[kind].append(compact(d))
            data[kind].sort(key=lambda d:d['id'])
        db.add(Row(user_id=uid,entity='sessions',client_id=cid,version=obj.version,data=None if obj.deleted_at else data))
    db.add(Row(user_id=uid,entity='meta',client_id='initialized',version=1,data={}))
    db.flush()
