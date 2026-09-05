from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.schemas.training import (
    TrainingExerciseCreate,
    TrainingExerciseResponse,
    TrainingExerciseUpdate,
    TrainingSessionCreate,
    TrainingSessionResponse,
    TrainingSessionSummary,
    TrainingSessionUpdate,
    TrainingSettingsResponse,
    TrainingSettingsUpsert,
    TrainingTemplateCreate,
    TrainingTemplateResponse,
    TrainingTemplateSummary,
)
from app.services import training_service

router = APIRouter(prefix="/api/v1/training", tags=["training"])


@router.get("/settings", response_model=TrainingSettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.get_settings(db, user)


@router.put("/settings", response_model=TrainingSettingsResponse)
def upsert_settings(
    payload: TrainingSettingsUpsert,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.upsert_settings(db, user, payload)


@router.post("/exercises", response_model=TrainingExerciseResponse, status_code=status.HTTP_201_CREATED)
def create_exercise(
    payload: TrainingExerciseCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.create_exercise(db, user, payload)


@router.get("/exercises", response_model=list[TrainingExerciseResponse])
def list_exercises(
    favorite_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.list_exercises(db, user, favorite_only=favorite_only)


@router.get("/exercises/{exercise_id}", response_model=TrainingExerciseResponse)
def get_exercise(
    exercise_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.get_exercise(db, user, exercise_id)


@router.patch("/exercises/{exercise_id}", response_model=TrainingExerciseResponse)
def update_exercise(
    exercise_id: UUID,
    payload: TrainingExerciseUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.update_exercise(db, user, exercise_id, payload)


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(
    exercise_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    training_service.delete_exercise(db, user, exercise_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/templates", response_model=TrainingTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: TrainingTemplateCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.create_template(db, user, payload)


@router.get("/templates", response_model=list[TrainingTemplateSummary])
def list_templates(
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.list_templates(db, user)


@router.get("/templates/{template_id}", response_model=TrainingTemplateResponse)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.get_template(db, user, template_id)


@router.put("/templates/{template_id}", response_model=TrainingTemplateResponse)
def replace_template(
    template_id: UUID,
    payload: TrainingTemplateCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.replace_template(db, user, template_id, payload)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    training_service.delete_template(db, user, template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions", response_model=TrainingSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: TrainingSessionCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.create_session(db, user, payload)


@router.get("/sessions", response_model=list[TrainingSessionSummary])
def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.list_sessions(db, user, limit)


@router.get("/sessions/{session_id}", response_model=TrainingSessionResponse)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.get_session(db, user, session_id)


@router.patch("/sessions/{session_id}", response_model=TrainingSessionResponse)
def update_session(
    session_id: UUID,
    payload: TrainingSessionUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return training_service.update_session(db, user, session_id, payload)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    training_service.delete_session(db, user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
