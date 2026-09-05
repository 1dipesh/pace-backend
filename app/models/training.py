import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class TrainingExercise(TimestampMixin, Base):
    __tablename__ = "training_exercises"
    __table_args__ = (
        CheckConstraint(
            "exercise_type IN ('weighted', 'bodyweight', 'duration')",
            name="ck_training_exercises_type",
        ),
        Index("ix_training_exercises_user_name", "user_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    exercise_type: Mapped[str] = mapped_column(String(16), nullable=False)
    primary_muscle: Mapped[str] = mapped_column(String(80), nullable=False)
    equipment: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingSettings(TimestampMixin, Base):
    __tablename__ = "training_settings"
    __table_args__ = (
        CheckConstraint(
            "effort_mode IN ('off', 'rir', 'rpe')",
            name="ck_training_settings_effort_mode",
        ),
        CheckConstraint(
            "default_warmup_rest_seconds >= 0",
            name="ck_training_settings_warmup_rest",
        ),
        CheckConstraint(
            "default_working_rest_seconds >= 0",
            name="ck_training_settings_working_rest",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pace_users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    default_warmup_rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60, server_default="60")
    default_working_rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=120, server_default="120")
    effort_mode: Mapped[str] = mapped_column(String(8), nullable=False, default="rir", server_default="rir")
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingTemplate(TimestampMixin, Base):
    __tablename__ = "training_templates"
    __table_args__ = (
        Index("ix_training_templates_user_name", "user_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_program_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_program_variant_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_program_day_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_program_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingTemplateExercise(TimestampMixin, Base):
    __tablename__ = "training_template_exercises"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_training_template_exercises_position"),
        Index("ix_training_template_exercises_template_position", "template_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_exercises.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingTemplateSet(TimestampMixin, Base):
    __tablename__ = "training_template_sets"
    __table_args__ = (
        CheckConstraint("set_type IN ('warmup', 'working')", name="ck_training_template_sets_type"),
        CheckConstraint("position >= 0", name="ck_training_template_sets_position"),
        CheckConstraint("target_reps IS NULL OR target_reps >= 0", name="ck_training_template_sets_reps"),
        CheckConstraint("target_weight IS NULL OR target_weight >= 0", name="ck_training_template_sets_weight"),
        CheckConstraint(
            "target_duration_seconds IS NULL OR target_duration_seconds >= 0",
            name="ck_training_template_sets_duration",
        ),
        CheckConstraint(
            "weight_unit IS NULL OR weight_unit IN ('kg', 'lb')",
            name="ck_training_template_sets_weight_unit",
        ),
        Index("ix_training_template_sets_exercise_position", "template_exercise_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_template_exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    set_type: Mapped[str] = mapped_column(String(8), nullable=False)
    target_reps: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    target_weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    weight_unit: Mapped[str | None] = mapped_column(String(4), nullable=True)
    target_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingSession(TimestampMixin, Base):
    __tablename__ = "training_sessions"
    __table_args__ = (
        Index("ix_training_sessions_user_started", "user_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingSessionExercise(TimestampMixin, Base):
    __tablename__ = "training_session_exercises"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_training_session_exercises_position"),
        CheckConstraint(
            "exercise_type_snapshot IN ('weighted', 'bodyweight', 'duration')",
            name="ck_training_session_exercises_type",
        ),
        Index("ix_training_session_exercises_session_position", "session_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_exercises.id", ondelete="SET NULL"), nullable=True, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    exercise_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    exercise_type_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    primary_muscle_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rest_override_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrainingSet(TimestampMixin, Base):
    __tablename__ = "training_sets"
    __table_args__ = (
        CheckConstraint("set_type IN ('warmup', 'working')", name="ck_training_sets_type"),
        CheckConstraint("position >= 0", name="ck_training_sets_position"),
        CheckConstraint("weight IS NULL OR weight >= 0", name="ck_training_sets_weight"),
        CheckConstraint("reps IS NULL OR reps >= 0", name="ck_training_sets_reps"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_training_sets_duration",
        ),
        CheckConstraint(
            "weight_unit IS NULL OR weight_unit IN ('kg', 'lb')",
            name="ck_training_sets_weight_unit",
        ),
        CheckConstraint(
            "effort_mode IN ('off', 'rir', 'rpe')",
            name="ck_training_sets_effort_mode",
        ),
        CheckConstraint("rir IS NULL OR (rir >= 0 AND rir <= 10)", name="ck_training_sets_rir"),
        CheckConstraint("rpe IS NULL OR (rpe >= 1 AND rpe <= 10)", name="ck_training_sets_rpe"),
        CheckConstraint(
            "rest_seconds IS NULL OR rest_seconds >= 0",
            name="ck_training_sets_rest",
        ),
        Index("ix_training_sets_session_exercise_position", "session_exercise_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("training_session_exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    set_type: Mapped[str] = mapped_column(String(8), nullable=False)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    weight_unit: Mapped[str | None] = mapped_column(String(4), nullable=True)
    reps: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effort_mode: Mapped[str] = mapped_column(String(8), nullable=False, default="off", server_default="off")
    rir: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    rpe: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
