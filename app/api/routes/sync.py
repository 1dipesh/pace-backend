import hashlib
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.models.profile import PaceProfile
from app.models.sync import SyncReceipt
from app.schemas.profile import PaceProfileCreate
from app.services.profile_service import to_response

def no_cache(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(prefix="/api/v1/sync", tags=["sync"], dependencies=[Depends(no_cache)])


class ProfileMutation(BaseModel):
    mutation_id: UUID
    expected_version: int = Field(ge=0)
    profile: PaceProfileCreate


def envelope(profile):
    return {
        "version": profile.version if profile else 0,
        "profile": to_response(profile).model_dump(mode="json") if profile and not profile.deleted_at else None,
        "deleted": bool(profile and profile.deleted_at),
    }


@router.get("/profile")
def read_profile(db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    profile = db.scalar(select(PaceProfile).where(PaceProfile.user_id == user.id))
    return envelope(profile)


@router.put("/profile")
def write_profile(payload: ProfileMutation, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    # Lock the account, including when no profile exists yet. All profile write
    # paths take this lock; a receipt and its mutation commit atomically.
    db.execute(select(PaceUser.id).where(PaceUser.id == user.id).with_for_update()).scalar_one()
    fingerprint = hashlib.sha256(json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()).hexdigest()
    receipt = db.get(SyncReceipt, (user.id, payload.mutation_id))
    if receipt:
        if receipt.fingerprint != fingerprint:
            raise HTTPException(409, detail={"code": "mutation_id_reused"})
        return receipt.response
    profile = db.scalar(select(PaceProfile).where(PaceProfile.user_id == user.id))
    current = envelope(profile)
    if current["version"] != payload.expected_version:
        raise HTTPException(409, detail={"code": "profile_conflict", "current": current})
    values = payload.profile.model_dump()
    if profile is None:
        profile = PaceProfile(user_id=user.id, **values)
        db.add(profile)
    else:
        for field, value in values.items():
            setattr(profile, field, value)
        profile.deleted_at = None
        profile.version += 1
    db.flush()
    db.refresh(profile)
    response = envelope(profile)
    db.add(SyncReceipt(user_id=user.id, mutation_id=payload.mutation_id, fingerprint=fingerprint, response=response))
    db.commit()
    return response
