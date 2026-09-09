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
from app.models.nutrition_sync import NutritionSyncRecord as Row
from app.schemas.nutrition_sync import Mutation
from app.services.nutrition_sync_service import lock, bootstrap, record, project

router = APIRouter(prefix="/api/v1/sync/nutrition", tags=["sync"], dependencies=[Depends(no_cache)])


def rows(db, uid):
    return db.scalars(select(Row).where(Row.user_id == uid, Row.entity != "meta")).all()


@router.get("")
def read(db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    lock(db, user.id)
    bootstrap(db, user.id)
    result = {"records": [record(r) for r in rows(db, user.id)]}
    db.commit()
    return result


@router.put("")
def write(payload: Mutation, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    lock(db, user.id)
    fingerprint = hashlib.sha256(("nutrition:" + json.dumps(payload.model_dump(mode="json"), sort_keys=True)).encode()).hexdigest()
    receipt = db.get(SyncReceipt, (user.id, payload.mutation_id))
    if receipt:
        if receipt.fingerprint != fingerprint:
            raise HTTPException(409, detail={"code": "mutation_id_reused"})
        return receipt.response
    bootstrap(db, user.id)
    current = {(r.entity, r.client_id): r for r in rows(db, user.id)}
    conflicts = []
    for c in payload.changes:
        row = current.get((c.entity, c.id))
        if (row.version if row else 0) != c.expected_version:
            conflicts.append(record(row) if row else dict(entity=c.entity, id=c.id, version=0, data=None))
    if conflicts:
        raise HTTPException(409, detail={"code": "nutrition_conflict", "current": conflicts})
    final = {k: r.data for k, r in current.items()}
    final.update({(c.entity, c.id): c.data for c in payload.changes})
    # Validate the complete resulting graph, not request order. Historical
    # entries keep snapshots even after their meal template is deleted.
    for (entity, cid), data in final.items():
        if data is None: continue
        refs = [i["foodId"] for i in data["items"]] if entity == "meals" else ([data["foodId"]] if entity == "entries" else [])
        if any(not final.get(("foods", ref)) for ref in refs):
            raise HTTPException(422, detail={"code": "missing_food", "entity": entity, "id": cid,
                "message": "Sync referenced foods first; remove references before deleting a food."})
    changed = []
    for c in sorted(payload.changes, key=lambda c: {"foods": 0, "goals": 1, "meals": 2, "entries": 3}[c.entity]):
        row = current.get((c.entity, c.id))
        if not row:
            row = Row(user_id=user.id, entity=c.entity, client_id=c.id, version=0)
            db.add(row)
        row.version += 1
        row.data = c.data
        project(db, user.id, c.entity, c.id, c.data, row.version)
        changed.append(record(row))
    result = {"records": changed}
    db.add(SyncReceipt(user_id=user.id, mutation_id=payload.mutation_id, fingerprint=fingerprint, response=result))
    db.commit()
    return result
