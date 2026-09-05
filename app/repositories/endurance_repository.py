from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.endurance import CardioActivity, HybridSegment, HybridSession
from app.schemas.endurance import (
    CardioActivityCreate,
    CardioActivityUpdate,
    HybridSessionCreate,
    HybridSessionUpdate,
)


def soft_delete(db: Session, row) -> None:
    row.deleted_at = datetime.now(timezone.utc)
    row.version += 1
    db.commit()


def create_cardio_activity(db: Session, user_id: UUID, payload: CardioActivityCreate):
    row = CardioActivity(user_id=user_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_cardio_activity(db: Session, user_id: UUID, activity_id: UUID):
    return db.scalar(
        select(CardioActivity).where(
            CardioActivity.id == activity_id,
            CardioActivity.user_id == user_id,
            CardioActivity.deleted_at.is_(None),
        )
    )


def list_cardio_activities(
    db: Session,
    user_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    activity_type: str | None = None,
    limit: int = 100,
):
    stmt = select(CardioActivity).where(
        CardioActivity.user_id == user_id,
        CardioActivity.deleted_at.is_(None),
    )
    if from_date is not None:
        stmt = stmt.where(CardioActivity.activity_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(CardioActivity.activity_date <= to_date)
    if activity_type is not None:
        stmt = stmt.where(CardioActivity.activity_type == activity_type)
    return list(
        db.scalars(
            stmt.order_by(CardioActivity.activity_date.desc(), CardioActivity.created_at.desc()).limit(limit)
        ).all()
    )


def update_cardio_activity(db: Session, row: CardioActivity, payload: CardioActivityUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def create_hybrid_session(db: Session, user_id: UUID, payload: HybridSessionCreate):
    values = payload.model_dump(exclude={"segments"})
    row = HybridSession(user_id=user_id, **values)
    db.add(row)
    db.flush()

    for item in payload.segments:
        db.add(HybridSegment(user_id=user_id, session_id=row.id, **item.model_dump()))

    db.commit()
    db.refresh(row)
    return row


def get_hybrid_session(db: Session, user_id: UUID, session_id: UUID):
    return db.scalar(
        select(HybridSession).where(
            HybridSession.id == session_id,
            HybridSession.user_id == user_id,
            HybridSession.deleted_at.is_(None),
        )
    )


def list_hybrid_sessions(db: Session, user_id: UUID, *, session_type: str | None = None, limit: int = 50):
    stmt = select(HybridSession).where(
        HybridSession.user_id == user_id,
        HybridSession.deleted_at.is_(None),
    )
    if session_type is not None:
        stmt = stmt.where(HybridSession.session_type == session_type)
    return list(db.scalars(stmt.order_by(HybridSession.started_at.desc()).limit(limit)).all())


def get_hybrid_segments(db: Session, user_id: UUID, session_id: UUID):
    return list(
        db.scalars(
            select(HybridSegment)
            .where(
                HybridSegment.user_id == user_id,
                HybridSegment.session_id == session_id,
                HybridSegment.deleted_at.is_(None),
            )
            .order_by(HybridSegment.position.asc())
        ).all()
    )


def update_hybrid_session(db: Session, row: HybridSession, payload: HybridSessionUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def replace_hybrid_session(db: Session, row: HybridSession, user_id: UUID, payload: HybridSessionCreate):
    for field, value in payload.model_dump(exclude={"segments"}).items():
        setattr(row, field, value)
    row.version += 1

    now = datetime.now(timezone.utc)
    for segment in get_hybrid_segments(db, user_id, row.id):
        segment.deleted_at = now
        segment.version += 1

    for item in payload.segments:
        db.add(HybridSegment(user_id=user_id, session_id=row.id, **item.model_dump()))

    db.commit()
    db.refresh(row)
    return row
