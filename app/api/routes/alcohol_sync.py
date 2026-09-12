import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.api.routes.sync import no_cache
from app.db.session import get_db
from app.models.user import PaceUser
from app.models.sync import SyncReceipt
from app.models.alcohol_sync import AlcoholSyncRecord as Row
from app.schemas.alcohol_sync import Mutation
from app.services.alcohol_sync_service import lock, bootstrap, envelope, project

router=APIRouter(prefix='/api/v1/sync/alcohol',tags=['sync'],dependencies=[Depends(no_cache)])


def rows(db,uid):
    return db.scalars(select(Row).where(Row.user_id==uid,Row.entity!='meta')).all()


@router.get('')
def read(db:Session=Depends(get_db),user:PaceUser=Depends(get_current_user)):
    lock(db,user.id); bootstrap(db,user.id)
    response={'records':[envelope(r) for r in rows(db,user.id)]}
    db.commit(); return response


@router.put('')
def write(payload:Mutation,db:Session=Depends(get_db),user:PaceUser=Depends(get_current_user)):
    lock(db,user.id)
    fingerprint=hashlib.sha256(('alcohol:'+json.dumps(payload.model_dump(mode='json'),sort_keys=True)).encode()).hexdigest()
    receipt=db.get(SyncReceipt,(user.id,payload.mutation_id))
    if receipt:
        if receipt.fingerprint!=fingerprint: raise HTTPException(409,detail={'code':'mutation_id_reused'})
        return receipt.response
    bootstrap(db,user.id)
    current={(r.entity,r.client_id):r for r in rows(db,user.id)}
    conflicts=[]
    for c in payload.changes:
        r=current.get((c.entity,c.id))
        if (r.version if r else 0)!=c.expected_version:
            conflicts.append(envelope(r) if r else dict(entity=c.entity,id=c.id,version=0,data=None))
    if conflicts: raise HTTPException(409,detail={'code':'alcohol_conflict','current':conflicts})
    final={k:r.data for k,r in current.items()}
    final.update({(c.entity,c.id):c.data for c in payload.changes})
    child_ids=set()
    for (entity,cid),data in final.items():
        if entity != 'sessions' or data is None: continue
        for kind in ('drinks','water','breaks'):
            for item in data[kind]:
                key=(kind,item['id'])
                if key in child_ids: raise HTTPException(422,detail={'code':'duplicate_session_child','id':cid})
                child_ids.add(key)
    changed=[]
    for c in payload.changes:
        row=current.get((c.entity,c.id))
        if not row: row=Row(user_id=user.id,entity=c.entity,client_id=c.id,version=0); db.add(row)
        row.version+=1; row.data=c.data
        project(db,user.id,c.entity,c.id,c.data,row.version)
        changed.append(envelope(row))
    response={'records':changed}
    db.add(SyncReceipt(user_id=user.id,mutation_id=payload.mutation_id,fingerprint=fingerprint,response=response))
    db.commit(); return response
