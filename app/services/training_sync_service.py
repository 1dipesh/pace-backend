"""Completed Training records synchronize as atomic documents.

Workout logs/sets and hybrid splits travel with their parent so an upload cannot
leave a partially restored workout. Active sessions remain on their recorder.
"""
from datetime import datetime, timezone, date
from uuid import UUID, uuid5
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.models.training_sync import TrainingSyncRecord as Row
from app.models.training import (TrainingExercise, TrainingSettings, TrainingTemplate, TrainingTemplateExercise,
    TrainingTemplateSet, TrainingSession, TrainingSessionExercise, TrainingSet)
from app.models.endurance import CardioActivity, HybridSession, HybridSegment
from app.services.nutrition_sync_service import lock, iso

MODELS = dict(exercises=TrainingExercise, templates=TrainingTemplate, workouts=TrainingSession, settings=TrainingSettings, activities=CardioActivity, hybrid=HybridSession)
MODES = {'weight_reps':'weighted','bodyweight_reps':'bodyweight','duration':'duration'}
REVERSE_MODES = {v:k for k,v in MODES.items()}
MUSCLES = {'chest','back','shoulders','biceps','triceps','quads','hamstrings','glutes','calves','core','full-body','other'}
EQUIPMENT = {'barbell','dumbbell','machine','cable','bodyweight','kettlebell','smith-machine','other'}


def legacy_guard(request: Request, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        lock(db, user.id)
        if db.get(Row, (user.id,'meta','initialized')):
            raise HTTPException(409, detail={'code':'training_sync_required','message':'Use /api/v1/sync/training for Training writes.'})


def mapped_id(uid, entity, cid):
    try: return UUID(cid)
    except ValueError: return uuid5(uid, f'training:{entity}:{cid}')


def child_id(uid, entity, parent, cid):
    return uuid5(uid, f'training-child:{entity}:{parent}:{cid}')


def time(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')) if value else None


def envelope(row):
    return dict(entity=row.entity,id=row.client_id,version=row.version,data=row.data)


def owned(db, model, uid, oid):
    obj=db.get(model,oid)
    if obj and obj.user_id != uid: raise HTTPException(422,detail={'code':'record_id_collision'})
    return obj


def stamp(obj, data, version):
    obj.deleted_at=None
    obj.version=version
    obj.client_updated_at=time(data.get('updatedAt'))
    if data.get('createdAt'): obj.created_at=time(data['createdAt'])


def children(db, model, uid, field, parent):
    return db.scalars(select(model).where(model.user_id==uid,getattr(model,field)==parent)).all()


def mark_children_deleted(db, model, uid, field, parent):
    for obj in children(db,model,uid,field,parent):
        obj.deleted_at=datetime.now(timezone.utc)
        obj.version+=1


def project(db, uid, entity, cid, data, version):
    model=MODELS[entity]
    oid=mapped_id(uid,entity,cid)
    obj=db.scalar(select(model).where(model.user_id==uid)) if entity=='settings' else owned(db,model,uid,oid)
    if data is None:
        if obj:
            obj.deleted_at=datetime.now(timezone.utc); obj.version=version
            if entity=='workouts':
                for log in children(db,TrainingSessionExercise,uid,'session_id',obj.id):
                    mark_children_deleted(db,TrainingSet,uid,'session_exercise_id',log.id)
                    log.deleted_at=obj.deleted_at
            if entity=='templates':
                for item in children(db,TrainingTemplateExercise,uid,'template_id',obj.id):
                    mark_children_deleted(db,TrainingTemplateSet,uid,'template_exercise_id',item.id)
                    item.deleted_at=obj.deleted_at
            if entity=='hybrid': mark_children_deleted(db,HybridSegment,uid,'session_id',obj.id)
        db.flush(); return
    if not obj: obj=model(id=oid,user_id=uid); db.add(obj)
    root=data['session'] if entity=='workouts' else data
    stamp(obj,root,version)
    if entity!='settings': obj.name=root['name']
    if hasattr(obj,'notes'): obj.notes=root.get('notes')
    if entity=='exercises':
        obj.exercise_type=MODES[data['trackingMode']]
        obj.primary_muscle=data['primaryMuscle']; obj.equipment=data['equipment']
        obj.is_favorite=bool(data.get('isFavorite'))
        obj.deleted_at=time(data.get('archivedAt'))
    elif entity=='settings':
        obj.effort_mode=data['effortMode']
        obj.default_working_rest_seconds=data['workingRestSeconds']; obj.default_warmup_rest_seconds=data['warmupRestSeconds']
    elif entity=='templates':
        for src,dst in [('sourceProgramId','source_program_id'),('sourceProgramVariantId','source_program_variant_id'),('sourceProgramDayId','source_program_day_id'),('sourceProgramName','source_program_name')]: setattr(obj,dst,data.get(src))
    elif entity=='activities':
        obj.activity_type=data['type']; obj.activity_date=date.fromisoformat(data['date'])
        obj.duration_seconds=data['durationSeconds']; obj.distance_km=data.get('distanceKm')
    else:
        obj.started_at=time(root['startedAt']); obj.completed_at=time(root['endedAt'])
        if entity=='workouts':
            tid=root.get('templateId')
            target=owned(db,TrainingTemplate,uid,mapped_id(uid,'templates',tid)) if tid else None
            obj.template_id=target.id if target else None
        else:
            obj.session_type='hyrox_stations_only' if data['preset']=='hyrox_stations' else data['preset']
            obj.total_duration_seconds=max(0,int((obj.completed_at-obj.started_at).total_seconds()))
    db.flush()
    if entity=='templates':
        for old in children(db,TrainingTemplateExercise,uid,'template_id',obj.id):
            mark_children_deleted(db,TrainingTemplateSet,uid,'template_exercise_id',old.id); old.deleted_at=datetime.now(timezone.utc)
        for i,item in enumerate(data['items']):
            iid=child_id(uid,'template-item',cid,str(i))
            target=owned(db,TrainingTemplateExercise,uid,iid) or TrainingTemplateExercise(id=iid,user_id=uid,template_id=obj.id)
            db.add(target); target.deleted_at=None
            target.exercise_id=mapped_id(uid,'exercises',item['exerciseId']); target.position=item['order']; target.notes=item.get('note'); db.flush()
            types=['warmup']*(item.get('warmupSets') or 0)+['working']*item['targetSets']
            for n,typ in enumerate(types):
                sid=child_id(uid,'template-set',cid,f'{i}:{n}')
                st=owned(db,TrainingTemplateSet,uid,sid) or TrainingTemplateSet(id=sid,user_id=uid,template_exercise_id=iid)
                db.add(st); st.deleted_at=None; st.position=n; st.set_type=typ
    elif entity=='workouts':
        for old in children(db,TrainingSessionExercise,uid,'session_id',obj.id):
            mark_children_deleted(db,TrainingSet,uid,'session_exercise_id',old.id); old.deleted_at=datetime.now(timezone.utc)
        for bundle in data['exercises']:
            log=bundle['log']; lid=child_id(uid,'log',cid,log['id'])
            row=owned(db,TrainingSessionExercise,uid,lid) or TrainingSessionExercise(id=lid,user_id=uid,session_id=obj.id)
            db.add(row); stamp(row,log,version)
            exercise=owned(db,TrainingExercise,uid,mapped_id(uid,'exercises',log['exerciseId']))
            row.exercise_id=exercise.id if exercise else None
            row.position=log['order']; row.exercise_name_snapshot=log['exerciseName']; row.exercise_type_snapshot=MODES[log.get('trackingMode') or 'weight_reps']
            row.primary_muscle_snapshot=log.get('primaryMuscle') or 'other'; row.notes=log.get('notes'); row.rest_override_seconds=log.get('restSeconds'); db.flush()
            for st in bundle['sets']:
                sid=child_id(uid,'set',cid,st['id'])
                target=owned(db,TrainingSet,uid,sid) or TrainingSet(id=sid,user_id=uid,session_exercise_id=lid)
                db.add(target); stamp(target,st,version)
                target.position=st['setNumber']-1; target.set_type=st['setType']; target.weight=st.get('weight'); target.weight_unit=st.get('weightUnit'); target.reps=st.get('reps')
                target.duration_seconds=st.get('durationSeconds'); target.rest_seconds=st.get('restSeconds'); target.completed_at=time(st.get('completedAt'))
                target.effort_mode=(st.get('effortMode') or 'off') if st.get('effortValue') is not None else 'off'; target.rir=st.get('effortValue') if target.effort_mode=='rir' else None; target.rpe=st.get('effortValue') if target.effort_mode=='rpe' else None
    elif entity=='hybrid':
        mark_children_deleted(db,HybridSegment,uid,'session_id',obj.id)
        for st in data['segments']:
            sid=child_id(uid,'segment',cid,st['id'])
            row=owned(db,HybridSegment,uid,sid) or HybridSegment(id=sid,user_id=uid,session_id=obj.id)
            db.add(row); row.deleted_at=None; row.position=st['order']; row.segment_type=st['kind']; row.segment_name=st['label']; row.station_key=st.get('stationType')
            row.target_distance_m=round(st['targetDistanceMeters']) if st.get('targetDistanceMeters') is not None else None
            row.target_reps=st.get('targetReps'); row.load=st.get('loadKg'); row.load_unit='kg' if row.load is not None else None
            row.started_at=time(st.get('startedAt')); row.completed_at=time(st.get('completedAt')); row.duration_seconds=st.get('durationSeconds')
    db.flush()


def base(obj, cid=None):
    return dict(id=cid or str(obj.id),createdAt=iso(obj.created_at),updatedAt=iso(obj.client_updated_at or obj.updated_at))


def compact(data):
    return {k:v for k,v in data.items() if v is not None}


def live(items): return [o for o in items if not o.deleted_at]


def bootstrap(db,uid):
    if db.get(Row,(uid,'meta','initialized')): return
    # Do not strand legacy in-progress API sessions behind a write guard.
    for model in (TrainingSession,HybridSession):
        if db.scalar(select(model.id).where(model.user_id==uid,model.deleted_at.is_(None),model.completed_at.is_(None)).limit(1)):
            raise HTTPException(409,detail={'code':'legacy_active_training','message':'Finish or discard the active workout created through the older API before enabling Training sync.'})
    for entity,model in MODELS.items():
        for obj in db.scalars(select(model).where(model.user_id==uid)).all():
            cid='default' if entity=='settings' else str(obj.id)
            data=base(obj,cid)
            if entity=='exercises':
                data.update(name=obj.name,primaryMuscle=obj.primary_muscle if obj.primary_muscle in MUSCLES else 'other',secondaryMuscles=[],equipment=obj.equipment if obj.equipment in EQUIPMENT else 'other',trackingMode=REVERSE_MODES[obj.exercise_type],isStarter=False,isFavorite=obj.is_favorite)
                if obj.deleted_at: data['archivedAt']=iso(obj.deleted_at)
            elif entity=='settings':
                data.update(effortMode=obj.effort_mode,autoStartRestTimer=True,workingRestSeconds=obj.default_working_rest_seconds,warmupRestSeconds=obj.default_warmup_rest_seconds,
                    plateCalculatorUnit='kg',plateCalculatorKgBarWeight=20,plateCalculatorLbBarWeight=45,plateCalculatorKgPlates=[25,20,15,10,5,2.5,1.25],plateCalculatorLbPlates=[45,35,25,10,5,2.5])
            elif entity=='templates':
                items=[]
                for item in sorted(live(children(db,TrainingTemplateExercise,uid,'template_id',obj.id)),key=lambda x:x.position):
                    sets=live(children(db,TrainingTemplateSet,uid,'template_exercise_id',item.id))
                    items.append(compact(dict(exerciseId=str(item.exercise_id),order=item.position,targetSets=max(1,sum(s.set_type=='working' for s in sets)),warmupSets=sum(s.set_type=='warmup' for s in sets),note=item.notes)))
                data.update(name=obj.name,notes=obj.notes,items=items,sourceProgramId=obj.source_program_id,sourceProgramVariantId=obj.source_program_variant_id,sourceProgramDayId=obj.source_program_day_id,sourceProgramName=obj.source_program_name)
            elif entity=='activities':
                data.update(type=obj.activity_type,name=obj.name,date=obj.activity_date.isoformat(),durationSeconds=obj.duration_seconds,distanceKm=float(obj.distance_km) if obj.distance_km is not None else None,notes=obj.notes)
            else:
                data.update(status='completed',name=obj.name,date=obj.started_at.date().isoformat(),startedAt=iso(obj.started_at),endedAt=iso(obj.completed_at or obj.started_at),notes=obj.notes)
                if entity=='workouts':
                    if obj.template_id: data['templateId']=str(obj.template_id)
                    bundles=[]
                    for log in sorted(live(children(db,TrainingSessionExercise,uid,'session_id',obj.id)),key=lambda x:x.position):
                        eid=str(log.exercise_id) if log.exercise_id else f'legacy-snapshot-{log.id}'
                        lg=compact(dict(**base(log),sessionId=cid,exerciseId=eid,exerciseName=log.exercise_name_snapshot,order=log.position,trackingMode=REVERSE_MODES[log.exercise_type_snapshot],primaryMuscle=log.primary_muscle_snapshot if log.primary_muscle_snapshot in MUSCLES else 'other',notes=log.notes,restSeconds=log.rest_override_seconds))
                        sets=[]
                        for st in sorted(live(children(db,TrainingSet,uid,'session_exercise_id',log.id)),key=lambda x:x.position):
                            values=dict(**base(st),sessionId=cid,exerciseLogId=str(log.id),exerciseId=eid,setNumber=st.position+1,setType=st.set_type,weight=float(st.weight) if st.weight is not None else None,weightUnit=st.weight_unit,reps=st.reps,durationSeconds=st.duration_seconds,restSeconds=st.rest_seconds,completedAt=iso(st.completed_at) if st.completed_at else None)
                            effort=st.rir if st.effort_mode=='rir' else st.rpe
                            if st.effort_mode!='off': values.update(effortMode=st.effort_mode,effortValue=float(effort) if effort is not None else None)
                            sets.append(compact(values))
                        bundles.append(dict(log=lg,sets=sets))
                    data=dict(id=cid,session=compact(data),exercises=bundles)
                else:
                    segments=[]
                    for st in sorted(live(children(db,HybridSegment,uid,'session_id',obj.id)),key=lambda x:x.position):
                        load=float(st.load) if st.load is not None else None
                        if load is not None and st.load_unit=='lb': load*=0.45359237
                        segments.append(compact(dict(id=str(st.id),order=st.position,kind=st.segment_type,label=st.segment_name,stationType=st.station_key,targetDistanceMeters=st.target_distance_m,targetReps=st.target_reps,loadKg=load,startedAt=iso(st.started_at) if st.started_at else None,completedAt=iso(st.completed_at) if st.completed_at else None,durationSeconds=st.duration_seconds)))
                    data.update(preset='hyrox_stations' if obj.session_type=='hyrox_stations_only' else obj.session_type,segments=segments)
            data=compact(data)
            db.add(Row(user_id=uid,entity=entity,client_id=cid,version=obj.version,data=None if obj.deleted_at and entity!='exercises' else data))
    db.add(Row(user_id=uid,entity='meta',client_id='initialized',version=1,data={}))
    db.flush()
