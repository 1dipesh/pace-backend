from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.schemas.endurance import (
    CardioActivityCreate,
    CardioActivityResponse,
    CardioActivityType,
    CardioActivityUpdate,
    HybridSessionCreate,
    HybridSessionResponse,
    HybridSessionSummary,
    HybridSessionType,
    HybridSessionUpdate,
)
from app.services import endurance_service

router = APIRouter(prefix="/api/v1/training", tags=["cardio & hybrid"])


@router.post("/cardio/activities", response_model=CardioActivityResponse, status_code=status.HTTP_201_CREATED)
def create_cardio_activity(
    payload: CardioActivityCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.create_cardio_activity(db, user, payload)


@router.get("/cardio/activities", response_model=list[CardioActivityResponse])
def list_cardio_activities(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    activity_type: CardioActivityType | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.list_cardio_activities(
        db,
        user,
        from_date=from_date,
        to_date=to_date,
        activity_type=activity_type,
        limit=limit,
    )


@router.get("/cardio/activities/{activity_id}", response_model=CardioActivityResponse)
def get_cardio_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.get_cardio_activity(db, user, activity_id)


@router.patch("/cardio/activities/{activity_id}", response_model=CardioActivityResponse)
def update_cardio_activity(
    activity_id: UUID,
    payload: CardioActivityUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.update_cardio_activity(db, user, activity_id, payload)


@router.delete("/cardio/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cardio_activity(
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    endurance_service.delete_cardio_activity(db, user, activity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/hybrid/sessions", response_model=HybridSessionResponse, status_code=status.HTTP_201_CREATED)
def create_hybrid_session(
    payload: HybridSessionCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.create_hybrid_session(db, user, payload)


@router.get("/hybrid/sessions", response_model=list[HybridSessionSummary])
def list_hybrid_sessions(
    session_type: HybridSessionType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.list_hybrid_sessions(db, user, session_type, limit)


@router.get("/hybrid/sessions/{session_id}", response_model=HybridSessionResponse)
def get_hybrid_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.get_hybrid_session(db, user, session_id)


@router.patch("/hybrid/sessions/{session_id}", response_model=HybridSessionResponse)
def update_hybrid_session(
    session_id: UUID,
    payload: HybridSessionUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.update_hybrid_session(db, user, session_id, payload)


@router.put("/hybrid/sessions/{session_id}", response_model=HybridSessionResponse)
def replace_hybrid_session(
    session_id: UUID,
    payload: HybridSessionCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return endurance_service.replace_hybrid_session(db, user, session_id, payload)


@router.delete("/hybrid/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hybrid_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    endurance_service.delete_hybrid_session(db, user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
