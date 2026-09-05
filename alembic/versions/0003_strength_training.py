"""create strength training tables

Revision ID: 0003_strength_training
Revises: 0002_nutrition
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_strength_training"
down_revision: Union[str, Sequence[str], None] = "0002_nutrition"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sync_columns():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "training_exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("exercise_type", sa.String(length=16), nullable=False),
        sa.Column("primary_muscle", sa.String(length=80), nullable=False),
        sa.Column("equipment", sa.String(length=80), nullable=True),
        sa.Column("is_favorite", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("exercise_type IN ('weighted', 'bodyweight', 'duration')", name="ck_training_exercises_type"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_exercises_user_id", "training_exercises", ["user_id"])
    op.create_index("ix_training_exercises_user_name", "training_exercises", ["user_id", "name"])

    op.create_table(
        "training_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("default_warmup_rest_seconds", sa.Integer(), server_default="60", nullable=False),
        sa.Column("default_working_rest_seconds", sa.Integer(), server_default="120", nullable=False),
        sa.Column("effort_mode", sa.String(length=8), server_default="rir", nullable=False),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("effort_mode IN ('off', 'rir', 'rpe')", name="ck_training_settings_effort_mode"),
        sa.CheckConstraint("default_warmup_rest_seconds >= 0", name="ck_training_settings_warmup_rest"),
        sa.CheckConstraint("default_working_rest_seconds >= 0", name="ck_training_settings_working_rest"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_settings_user_id", "training_settings", ["user_id"], unique=True)

    op.create_table(
        "training_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_program_id", sa.String(length=120), nullable=True),
        sa.Column("source_program_variant_id", sa.String(length=120), nullable=True),
        sa.Column("source_program_day_id", sa.String(length=120), nullable=True),
        sa.Column("source_program_name", sa.String(length=160), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_templates_user_id", "training_templates", ["user_id"])
    op.create_index("ix_training_templates_user_name", "training_templates", ["user_id", "name"])

    op.create_table(
        "training_template_exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("position >= 0", name="ck_training_template_exercises_position"),
        sa.ForeignKeyConstraint(["exercise_id"], ["training_exercises.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["training_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_template_exercises_user_id", "training_template_exercises", ["user_id"])
    op.create_index("ix_training_template_exercises_template_id", "training_template_exercises", ["template_id"])
    op.create_index("ix_training_template_exercises_exercise_id", "training_template_exercises", ["exercise_id"])
    op.create_index(
        "ix_training_template_exercises_template_position",
        "training_template_exercises",
        ["template_id", "position"],
    )

    op.create_table(
        "training_template_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("template_exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("set_type", sa.String(length=8), nullable=False),
        sa.Column("target_reps", sa.SmallInteger(), nullable=True),
        sa.Column("target_weight", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("weight_unit", sa.String(length=4), nullable=True),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("set_type IN ('warmup', 'working')", name="ck_training_template_sets_type"),
        sa.CheckConstraint("position >= 0", name="ck_training_template_sets_position"),
        sa.CheckConstraint("target_reps IS NULL OR target_reps >= 0", name="ck_training_template_sets_reps"),
        sa.CheckConstraint("target_weight IS NULL OR target_weight >= 0", name="ck_training_template_sets_weight"),
        sa.CheckConstraint(
            "target_duration_seconds IS NULL OR target_duration_seconds >= 0",
            name="ck_training_template_sets_duration",
        ),
        sa.CheckConstraint("weight_unit IS NULL OR weight_unit IN ('kg', 'lb')", name="ck_training_template_sets_weight_unit"),
        sa.ForeignKeyConstraint(["template_exercise_id"], ["training_template_exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_template_sets_user_id", "training_template_sets", ["user_id"])
    op.create_index("ix_training_template_sets_template_exercise_id", "training_template_sets", ["template_exercise_id"])
    op.create_index(
        "ix_training_template_sets_exercise_position",
        "training_template_sets",
        ["template_exercise_id", "position"],
    )

    op.create_table(
        "training_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.ForeignKeyConstraint(["template_id"], ["training_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_sessions_user_id", "training_sessions", ["user_id"])
    op.create_index("ix_training_sessions_template_id", "training_sessions", ["template_id"])
    op.create_index("ix_training_sessions_user_started", "training_sessions", ["user_id", "started_at"])

    op.create_table(
        "training_session_exercises",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("exercise_id", sa.Uuid(), nullable=True),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("exercise_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("exercise_type_snapshot", sa.String(length=16), nullable=False),
        sa.Column("primary_muscle_snapshot", sa.String(length=80), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("rest_override_seconds", sa.Integer(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("position >= 0", name="ck_training_session_exercises_position"),
        sa.CheckConstraint(
            "exercise_type_snapshot IN ('weighted', 'bodyweight', 'duration')",
            name="ck_training_session_exercises_type",
        ),
        sa.ForeignKeyConstraint(["exercise_id"], ["training_exercises.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_session_exercises_user_id", "training_session_exercises", ["user_id"])
    op.create_index("ix_training_session_exercises_session_id", "training_session_exercises", ["session_id"])
    op.create_index("ix_training_session_exercises_exercise_id", "training_session_exercises", ["exercise_id"])
    op.create_index(
        "ix_training_session_exercises_session_position",
        "training_session_exercises",
        ["session_id", "position"],
    )

    op.create_table(
        "training_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_exercise_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("set_type", sa.String(length=8), nullable=False),
        sa.Column("weight", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("weight_unit", sa.String(length=4), nullable=True),
        sa.Column("reps", sa.SmallInteger(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("effort_mode", sa.String(length=8), server_default="off", nullable=False),
        sa.Column("rir", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("rpe", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("set_type IN ('warmup', 'working')", name="ck_training_sets_type"),
        sa.CheckConstraint("position >= 0", name="ck_training_sets_position"),
        sa.CheckConstraint("weight IS NULL OR weight >= 0", name="ck_training_sets_weight"),
        sa.CheckConstraint("reps IS NULL OR reps >= 0", name="ck_training_sets_reps"),
        sa.CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="ck_training_sets_duration"),
        sa.CheckConstraint("weight_unit IS NULL OR weight_unit IN ('kg', 'lb')", name="ck_training_sets_weight_unit"),
        sa.CheckConstraint("effort_mode IN ('off', 'rir', 'rpe')", name="ck_training_sets_effort_mode"),
        sa.CheckConstraint("rir IS NULL OR (rir >= 0 AND rir <= 10)", name="ck_training_sets_rir"),
        sa.CheckConstraint("rpe IS NULL OR (rpe >= 1 AND rpe <= 10)", name="ck_training_sets_rpe"),
        sa.CheckConstraint("rest_seconds IS NULL OR rest_seconds >= 0", name="ck_training_sets_rest"),
        sa.ForeignKeyConstraint(["session_exercise_id"], ["training_session_exercises.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_sets_user_id", "training_sets", ["user_id"])
    op.create_index("ix_training_sets_session_exercise_id", "training_sets", ["session_exercise_id"])
    op.create_index(
        "ix_training_sets_session_exercise_position",
        "training_sets",
        ["session_exercise_id", "position"],
    )


def downgrade() -> None:
    op.drop_table("training_sets")
    op.drop_table("training_session_exercises")
    op.drop_table("training_sessions")
    op.drop_table("training_template_sets")
    op.drop_table("training_template_exercises")
    op.drop_table("training_templates")
    op.drop_table("training_settings")
    op.drop_table("training_exercises")
