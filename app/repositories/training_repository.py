from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.training import (
    TrainingExercise,
    TrainingSession,
    TrainingSessionExercise,
    TrainingSet,
    TrainingSettings,
    TrainingTemplate,
    TrainingTemplateExercise,
    TrainingTemplateSet,
)
from app.schemas.training import (
    TrainingExerciseCreate,
    TrainingExerciseUpdate,
    TrainingSessionCreate,
    TrainingSessionUpdate,
    TrainingSettingsUpsert,
    TrainingTemplateCreate,
)


def get_exercise(db: Session, user_id: UUID, exercise_id: UUID, *, include_deleted: bool = False):
    stmt = select(TrainingExercise).where(
        TrainingExercise.id == exercise_id,
        TrainingExercise.user_id == user_id,
    )
    if not include_deleted:
        stmt = stmt.where(TrainingExercise.deleted_at.is_(None))
    return db.scalar(stmt)


def list_exercises(db: Session, user_id: UUID, *, favorite_only: bool = False):
    stmt = select(TrainingExercise).where(
        TrainingExercise.user_id == user_id,
        TrainingExercise.deleted_at.is_(None),
    )
    if favorite_only:
        stmt = stmt.where(TrainingExercise.is_favorite.is_(True))
    return list(db.scalars(stmt.order_by(TrainingExercise.name.asc())).all())


def create_exercise(db: Session, user_id: UUID, payload: TrainingExerciseCreate):
    exercise = TrainingExercise(user_id=user_id, **payload.model_dump())
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


def update_exercise(db: Session, exercise: TrainingExercise, payload: TrainingExerciseUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exercise, field, value)
    exercise.version += 1
    db.commit()
    db.refresh(exercise)
    return exercise


def soft_delete(db: Session, row) -> None:
    row.deleted_at = datetime.now(timezone.utc)
    row.version += 1
    db.commit()


def get_settings(db: Session, user_id: UUID):
    return db.scalar(
        select(TrainingSettings).where(
            TrainingSettings.user_id == user_id,
            TrainingSettings.deleted_at.is_(None),
        )
    )


def upsert_settings(db: Session, user_id: UUID, payload: TrainingSettingsUpsert):
    settings = db.scalar(select(TrainingSettings).where(TrainingSettings.user_id == user_id))
    values = payload.model_dump()
    if settings is None:
        settings = TrainingSettings(user_id=user_id, **values)
        db.add(settings)
    else:
        for field, value in values.items():
            setattr(settings, field, value)
        settings.deleted_at = None
        settings.version += 1
    db.commit()
    db.refresh(settings)
    return settings


def list_templates(db: Session, user_id: UUID):
    return list(
        db.scalars(
            select(TrainingTemplate)
            .where(
                TrainingTemplate.user_id == user_id,
                TrainingTemplate.deleted_at.is_(None),
            )
            .order_by(TrainingTemplate.updated_at.desc())
        ).all()
    )


def get_template(db: Session, user_id: UUID, template_id: UUID):
    return db.scalar(
        select(TrainingTemplate).where(
            TrainingTemplate.id == template_id,
            TrainingTemplate.user_id == user_id,
            TrainingTemplate.deleted_at.is_(None),
        )
    )


def get_template_exercises(db: Session, user_id: UUID, template_id: UUID):
    return list(
        db.scalars(
            select(TrainingTemplateExercise)
            .where(
                TrainingTemplateExercise.user_id == user_id,
                TrainingTemplateExercise.template_id == template_id,
                TrainingTemplateExercise.deleted_at.is_(None),
            )
            .order_by(TrainingTemplateExercise.position.asc())
        ).all()
    )


def get_template_sets(db: Session, user_id: UUID, template_exercise_id: UUID):
    return list(
        db.scalars(
            select(TrainingTemplateSet)
            .where(
                TrainingTemplateSet.user_id == user_id,
                TrainingTemplateSet.template_exercise_id == template_exercise_id,
                TrainingTemplateSet.deleted_at.is_(None),
            )
            .order_by(TrainingTemplateSet.position.asc())
        ).all()
    )


def create_template(db: Session, user_id: UUID, payload: TrainingTemplateCreate):
    values = payload.model_dump(exclude={"exercises"})
    template = TrainingTemplate(user_id=user_id, **values)
    db.add(template)
    db.flush()

    for exercise_input in payload.exercises:
        template_exercise = TrainingTemplateExercise(
            user_id=user_id,
            template_id=template.id,
            exercise_id=exercise_input.exercise_id,
            position=exercise_input.position,
            notes=exercise_input.notes,
            client_updated_at=exercise_input.client_updated_at,
        )
        db.add(template_exercise)
        db.flush()
        for set_input in exercise_input.sets:
            db.add(
                TrainingTemplateSet(
                    user_id=user_id,
                    template_exercise_id=template_exercise.id,
                    **set_input.model_dump(),
                )
            )

    db.commit()
    db.refresh(template)
    return template


def replace_template(db: Session, template: TrainingTemplate, user_id: UUID, payload: TrainingTemplateCreate):
    values = payload.model_dump(exclude={"exercises"})
    for field, value in values.items():
        setattr(template, field, value)
    template.version += 1

    existing_exercises = get_template_exercises(db, user_id, template.id)
    for item in existing_exercises:
        db.execute(delete(TrainingTemplateSet).where(TrainingTemplateSet.template_exercise_id == item.id))
    db.execute(delete(TrainingTemplateExercise).where(TrainingTemplateExercise.template_id == template.id))
    db.flush()

    for exercise_input in payload.exercises:
        template_exercise = TrainingTemplateExercise(
            user_id=user_id,
            template_id=template.id,
            exercise_id=exercise_input.exercise_id,
            position=exercise_input.position,
            notes=exercise_input.notes,
            client_updated_at=exercise_input.client_updated_at,
        )
        db.add(template_exercise)
        db.flush()
        for set_input in exercise_input.sets:
            db.add(
                TrainingTemplateSet(
                    user_id=user_id,
                    template_exercise_id=template_exercise.id,
                    **set_input.model_dump(),
                )
            )

    db.commit()
    db.refresh(template)
    return template


def list_sessions(db: Session, user_id: UUID, *, limit: int = 50):
    return list(
        db.scalars(
            select(TrainingSession)
            .where(
                TrainingSession.user_id == user_id,
                TrainingSession.deleted_at.is_(None),
            )
            .order_by(TrainingSession.started_at.desc())
            .limit(limit)
        ).all()
    )


def get_session(db: Session, user_id: UUID, session_id: UUID):
    return db.scalar(
        select(TrainingSession).where(
            TrainingSession.id == session_id,
            TrainingSession.user_id == user_id,
            TrainingSession.deleted_at.is_(None),
        )
    )


def get_session_exercises(db: Session, user_id: UUID, session_id: UUID):
    return list(
        db.scalars(
            select(TrainingSessionExercise)
            .where(
                TrainingSessionExercise.user_id == user_id,
                TrainingSessionExercise.session_id == session_id,
                TrainingSessionExercise.deleted_at.is_(None),
            )
            .order_by(TrainingSessionExercise.position.asc())
        ).all()
    )


def get_session_sets(db: Session, user_id: UUID, session_exercise_id: UUID):
    return list(
        db.scalars(
            select(TrainingSet)
            .where(
                TrainingSet.user_id == user_id,
                TrainingSet.session_exercise_id == session_exercise_id,
                TrainingSet.deleted_at.is_(None),
            )
            .order_by(TrainingSet.position.asc())
        ).all()
    )


def create_session(db: Session, user_id: UUID, payload: TrainingSessionCreate, exercises_by_id):
    values = payload.model_dump(exclude={"exercises"})
    session = TrainingSession(user_id=user_id, **values)
    db.add(session)
    db.flush()

    for exercise_input in payload.exercises:
        source = exercises_by_id[exercise_input.exercise_id]
        session_exercise = TrainingSessionExercise(
            user_id=user_id,
            session_id=session.id,
            exercise_id=source.id,
            position=exercise_input.position,
            exercise_name_snapshot=source.name,
            exercise_type_snapshot=source.exercise_type,
            primary_muscle_snapshot=source.primary_muscle,
            notes=exercise_input.notes,
            rest_override_seconds=exercise_input.rest_override_seconds,
            client_updated_at=exercise_input.client_updated_at,
        )
        db.add(session_exercise)
        db.flush()

        for set_input in exercise_input.sets:
            db.add(
                TrainingSet(
                    user_id=user_id,
                    session_exercise_id=session_exercise.id,
                    **set_input.model_dump(),
                )
            )

    db.commit()
    db.refresh(session)
    return session


def update_session(db: Session, session: TrainingSession, payload: TrainingSessionUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, field, value)
    session.version += 1
    db.commit()
    db.refresh(session)
    return session
