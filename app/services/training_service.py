from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import PaceUser
from app.repositories import training_repository as repo
from app.schemas.training import (
    TrainingExerciseCreate,
    TrainingExerciseResponse,
    TrainingExerciseUpdate,
    TrainingSessionCreate,
    TrainingSessionExerciseResponse,
    TrainingSessionResponse,
    TrainingSessionSetInput,
    TrainingSessionSummary,
    TrainingSessionUpdate,
    TrainingSettingsResponse,
    TrainingSettingsUpsert,
    TrainingSetResponse,
    TrainingTemplateCreate,
    TrainingTemplateExerciseResponse,
    TrainingTemplateResponse,
    TrainingTemplateSetResponse,
    TrainingTemplateSummary,
)


def _not_found(label: str):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def create_exercise(db: Session, user: PaceUser, payload: TrainingExerciseCreate):
    return TrainingExerciseResponse.model_validate(repo.create_exercise(db, user.id, payload))


def list_exercises(db: Session, user: PaceUser, favorite_only: bool = False):
    return [
        TrainingExerciseResponse.model_validate(item)
        for item in repo.list_exercises(db, user.id, favorite_only=favorite_only)
    ]


def get_exercise(db: Session, user: PaceUser, exercise_id: UUID):
    item = repo.get_exercise(db, user.id, exercise_id)
    if item is None:
        _not_found("Exercise")
    return TrainingExerciseResponse.model_validate(item)


def update_exercise(db: Session, user: PaceUser, exercise_id: UUID, payload: TrainingExerciseUpdate):
    item = repo.get_exercise(db, user.id, exercise_id)
    if item is None:
        _not_found("Exercise")
    if not payload.model_dump(exclude_unset=True):
        return TrainingExerciseResponse.model_validate(item)
    return TrainingExerciseResponse.model_validate(repo.update_exercise(db, item, payload))


def delete_exercise(db: Session, user: PaceUser, exercise_id: UUID):
    item = repo.get_exercise(db, user.id, exercise_id)
    if item is None:
        _not_found("Exercise")
    repo.soft_delete(db, item)


def get_settings(db: Session, user: PaceUser):
    item = repo.get_settings(db, user.id)
    if item is None:
        item = repo.upsert_settings(db, user.id, TrainingSettingsUpsert())
    return TrainingSettingsResponse.model_validate(item)


def upsert_settings(db: Session, user: PaceUser, payload: TrainingSettingsUpsert):
    return TrainingSettingsResponse.model_validate(repo.upsert_settings(db, user.id, payload))


def _require_exercises(db: Session, user: PaceUser, ids: set[UUID]):
    result = {}
    for exercise_id in ids:
        exercise = repo.get_exercise(db, user.id, exercise_id)
        if exercise is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Exercise {exercise_id} is not available",
            )
        result[exercise_id] = exercise
    return result


def _template_response(db: Session, user: PaceUser, template):
    exercise_rows = repo.get_template_exercises(db, user.id, template.id)
    nested = []
    for row in exercise_rows:
        exercise = repo.get_exercise(db, user.id, row.exercise_id, include_deleted=True)
        if exercise is None:
            continue
        sets = [
            TrainingTemplateSetResponse(
                id=s.id,
                position=s.position,
                set_type=s.set_type,
                target_reps=s.target_reps,
                target_weight=s.target_weight,
                weight_unit=s.weight_unit,
                target_duration_seconds=s.target_duration_seconds,
                client_updated_at=s.client_updated_at,
                version=s.version,
            )
            for s in repo.get_template_sets(db, user.id, row.id)
        ]
        nested.append(
            TrainingTemplateExerciseResponse(
                id=row.id,
                exercise_id=row.exercise_id,
                position=row.position,
                notes=row.notes,
                exercise_name=exercise.name,
                exercise_type=exercise.exercise_type,
                primary_muscle=exercise.primary_muscle,
                sets=sets,
                version=row.version,
            )
        )
    return TrainingTemplateResponse(
        id=template.id,
        user_id=template.user_id,
        name=template.name,
        notes=template.notes,
        source_program_id=template.source_program_id,
        source_program_variant_id=template.source_program_variant_id,
        source_program_day_id=template.source_program_day_id,
        source_program_name=template.source_program_name,
        exercises=nested,
        client_updated_at=template.client_updated_at,
        created_at=template.created_at,
        updated_at=template.updated_at,
        deleted_at=template.deleted_at,
        version=template.version,
    )


def create_template(db: Session, user: PaceUser, payload: TrainingTemplateCreate):
    _require_exercises(db, user, {item.exercise_id for item in payload.exercises})
    return _template_response(db, user, repo.create_template(db, user.id, payload))


def list_templates(db: Session, user: PaceUser):
    return [TrainingTemplateSummary.model_validate(item) for item in repo.list_templates(db, user.id)]


def get_template(db: Session, user: PaceUser, template_id: UUID):
    template = repo.get_template(db, user.id, template_id)
    if template is None:
        _not_found("Template")
    return _template_response(db, user, template)


def replace_template(db: Session, user: PaceUser, template_id: UUID, payload: TrainingTemplateCreate):
    template = repo.get_template(db, user.id, template_id)
    if template is None:
        _not_found("Template")
    _require_exercises(db, user, {item.exercise_id for item in payload.exercises})
    return _template_response(db, user, repo.replace_template(db, template, user.id, payload))


def delete_template(db: Session, user: PaceUser, template_id: UUID):
    template = repo.get_template(db, user.id, template_id)
    if template is None:
        _not_found("Template")
    repo.soft_delete(db, template)


def _session_response(db: Session, user: PaceUser, session):
    nested = []
    for row in repo.get_session_exercises(db, user.id, session.id):
        sets = [
            TrainingSetResponse(
                id=s.id,
                position=s.position,
                set_type=s.set_type,
                weight=s.weight,
                weight_unit=s.weight_unit,
                reps=s.reps,
                duration_seconds=s.duration_seconds,
                effort_mode=s.effort_mode,
                rir=s.rir,
                rpe=s.rpe,
                rest_seconds=s.rest_seconds,
                completed_at=s.completed_at,
                client_updated_at=s.client_updated_at,
                version=s.version,
            )
            for s in repo.get_session_sets(db, user.id, row.id)
        ]
        nested.append(
            TrainingSessionExerciseResponse(
                id=row.id,
                exercise_id=row.exercise_id,
                position=row.position,
                exercise_name_snapshot=row.exercise_name_snapshot,
                exercise_type_snapshot=row.exercise_type_snapshot,
                primary_muscle_snapshot=row.primary_muscle_snapshot,
                notes=row.notes,
                rest_override_seconds=row.rest_override_seconds,
                sets=sets,
                version=row.version,
            )
        )
    return TrainingSessionResponse(
        id=session.id,
        user_id=session.user_id,
        template_id=session.template_id,
        name=session.name,
        notes=session.notes,
        started_at=session.started_at,
        completed_at=session.completed_at,
        exercises=nested,
        client_updated_at=session.client_updated_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
        deleted_at=session.deleted_at,
        version=session.version,
    )


def create_session(db: Session, user: PaceUser, payload: TrainingSessionCreate):
    if payload.template_id is not None and repo.get_template(db, user.id, payload.template_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Template is not available",
        )
    exercise_map = _require_exercises(db, user, {item.exercise_id for item in payload.exercises})
    return _session_response(db, user, repo.create_session(db, user.id, payload, exercise_map))


def list_sessions(db: Session, user: PaceUser, limit: int):
    return [TrainingSessionSummary.model_validate(item) for item in repo.list_sessions(db, user.id, limit=limit)]


def get_session(db: Session, user: PaceUser, session_id: UUID):
    session = repo.get_session(db, user.id, session_id)
    if session is None:
        _not_found("Session")
    return _session_response(db, user, session)


def update_session(db: Session, user: PaceUser, session_id: UUID, payload: TrainingSessionUpdate):
    session = repo.get_session(db, user.id, session_id)
    if session is None:
        _not_found("Session")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _session_response(db, user, session)
    if payload.completed_at is not None and payload.completed_at < session.started_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="completed_at cannot be earlier than started_at",
        )
    session = repo.update_session(db, session, payload)
    return _session_response(db, user, session)


def delete_session(db: Session, user: PaceUser, session_id: UUID):
    session = repo.get_session(db, user.id, session_id)
    if session is None:
        _not_found("Session")
    repo.soft_delete(db, session)
