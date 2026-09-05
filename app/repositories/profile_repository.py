from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.profile import PaceProfile
from app.schemas.profile import PaceProfileCreate, PaceProfileUpdate


def get_profile(db: Session, user_id) -> PaceProfile | None:
    return db.scalar(
        select(PaceProfile).where(
            PaceProfile.user_id == user_id,
            PaceProfile.deleted_at.is_(None),
        )
    )


def get_profile_including_deleted(db: Session, user_id) -> PaceProfile | None:
    return db.scalar(select(PaceProfile).where(PaceProfile.user_id == user_id))


def create_profile(db: Session, user_id, payload: PaceProfileCreate) -> PaceProfile:
    existing = get_profile_including_deleted(db, user_id)
    values = payload.model_dump()

    if existing is not None:
        if existing.deleted_at is None:
            raise ValueError("profile_exists")
        for field, value in values.items():
            setattr(existing, field, value)
        existing.deleted_at = None
        existing.version += 1
        db.commit()
        db.refresh(existing)
        return existing

    profile = PaceProfile(user_id=user_id, **values)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(
    db: Session,
    profile: PaceProfile,
    payload: PaceProfileUpdate,
) -> PaceProfile:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    profile.version += 1
    db.commit()
    db.refresh(profile)
    return profile


def soft_delete_profile(db: Session, profile: PaceProfile) -> None:
    profile.deleted_at = datetime.now(timezone.utc)
    profile.version += 1
    db.commit()
