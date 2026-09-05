from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import PaceUser
from app.repositories import endurance_repository as repo
from app.schemas.endurance import (
    CardioActivityCreate,
    CardioActivityResponse,
    CardioActivityUpdate,
    HybridSegmentResponse,
    HybridSessionCreate,
    HybridSessionResponse,
    HybridSessionSummary,
    HybridSessionUpdate,
)


def _not_found(label: str):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def _cardio_response(row) -> CardioActivityResponse:
    distance = float(row.distance_km) if row.distance_km is not None else None
    pace = None
    speed = None
    if distance is not None and distance > 0:
        pace = row.duration_seconds / distance
        speed = distance / (row.duration_seconds / 3600)
    return CardioActivityResponse(
        id=row.id,
        user_id=row.user_id,
        activity_type=row.activity_type,
        name=row.name,
        activity_date=row.activity_date,
        duration_seconds=row.duration_seconds,
        distance_km=distance,
        notes=row.notes,
        client_updated_at=row.client_updated_at,
        pace_seconds_per_km=round(pace, 2) if pace is not None else None,
        average_speed_kmh=round(speed, 2) if speed is not None else None,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        version=row.version,
    )


def create_cardio_activity(db: Session, user: PaceUser, payload: CardioActivityCreate):
    return _cardio_response(repo.create_cardio_activity(db, user.id, payload))


def list_cardio_activities(
    db: Session,
    user: PaceUser,
    *,
    from_date: date | None,
    to_date: date | None,
    activity_type: str | None,
    limit: int,
):
    if from_date is not None and to_date is not None and to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to_date cannot be earlier than from_date",
        )
    return [
        _cardio_response(item)
        for item in repo.list_cardio_activities(
            db,
            user.id,
            from_date=from_date,
            to_date=to_date,
            activity_type=activity_type,
            limit=limit,
        )
    ]


def get_cardio_activity(db: Session, user: PaceUser, activity_id: UUID):
    row = repo.get_cardio_activity(db, user.id, activity_id)
    if row is None:
        _not_found("Cardio activity")
    return _cardio_response(row)


def update_cardio_activity(db: Session, user: PaceUser, activity_id: UUID, payload: CardioActivityUpdate):
    row = repo.get_cardio_activity(db, user.id, activity_id)
    if row is None:
        _not_found("Cardio activity")
    if not payload.model_dump(exclude_unset=True):
        return _cardio_response(row)
    return _cardio_response(repo.update_cardio_activity(db, row, payload))


def delete_cardio_activity(db: Session, user: PaceUser, activity_id: UUID):
    row = repo.get_cardio_activity(db, user.id, activity_id)
    if row is None:
        _not_found("Cardio activity")
    repo.soft_delete(db, row)


def _hybrid_response(db: Session, user: PaceUser, row) -> HybridSessionResponse:
    segments = [
        HybridSegmentResponse(
            id=item.id,
            position=item.position,
            segment_type=item.segment_type,
            segment_name=item.segment_name,
            station_key=item.station_key,
            target_distance_m=item.target_distance_m,
            target_reps=item.target_reps,
            load=float(item.load) if item.load is not None else None,
            load_unit=item.load_unit,
            started_at=item.started_at,
            completed_at=item.completed_at,
            duration_seconds=item.duration_seconds,
            notes=item.notes,
            client_updated_at=item.client_updated_at,
            version=item.version,
            created_at=item.created_at,
            updated_at=item.updated_at,
            deleted_at=item.deleted_at,
        )
        for item in repo.get_hybrid_segments(db, user.id, row.id)
    ]
    return HybridSessionResponse(
        id=row.id,
        user_id=row.user_id,
        session_type=row.session_type,
        name=row.name,
        started_at=row.started_at,
        completed_at=row.completed_at,
        total_duration_seconds=row.total_duration_seconds,
        notes=row.notes,
        segments=segments,
        client_updated_at=row.client_updated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        version=row.version,
    )


def create_hybrid_session(db: Session, user: PaceUser, payload: HybridSessionCreate):
    return _hybrid_response(db, user, repo.create_hybrid_session(db, user.id, payload))


def list_hybrid_sessions(db: Session, user: PaceUser, session_type: str | None, limit: int):
    return [
        HybridSessionSummary.model_validate(item)
        for item in repo.list_hybrid_sessions(db, user.id, session_type=session_type, limit=limit)
    ]


def get_hybrid_session(db: Session, user: PaceUser, session_id: UUID):
    row = repo.get_hybrid_session(db, user.id, session_id)
    if row is None:
        _not_found("Hybrid session")
    return _hybrid_response(db, user, row)


def update_hybrid_session(db: Session, user: PaceUser, session_id: UUID, payload: HybridSessionUpdate):
    row = repo.get_hybrid_session(db, user.id, session_id)
    if row is None:
        _not_found("Hybrid session")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _hybrid_response(db, user, row)
    completed_at = changes.get("completed_at")
    if completed_at is not None and completed_at < row.started_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="completed_at cannot be earlier than started_at",
        )
    return _hybrid_response(db, user, repo.update_hybrid_session(db, row, payload))


def replace_hybrid_session(db: Session, user: PaceUser, session_id: UUID, payload: HybridSessionCreate):
    row = repo.get_hybrid_session(db, user.id, session_id)
    if row is None:
        _not_found("Hybrid session")
    return _hybrid_response(db, user, repo.replace_hybrid_session(db, row, user.id, payload))


def delete_hybrid_session(db: Session, user: PaceUser, session_id: UUID):
    row = repo.get_hybrid_session(db, user.id, session_id)
    if row is None:
        _not_found("Hybrid session")
    repo.soft_delete(db, row)
