"""create cardio and hybrid tables

Revision ID: 0004_cardio_hybrid
Revises: 0003_strength_training
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_cardio_hybrid"
down_revision: Union[str, Sequence[str], None] = "0003_strength_training"
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
        "cardio_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint(
            "activity_type IN ('running', 'walking', 'cycling', 'football', 'basketball', 'rowing', 'swimming', 'other')",
            name="ck_cardio_activities_type",
        ),
        sa.CheckConstraint("duration_seconds > 0", name="ck_cardio_activities_duration"),
        sa.CheckConstraint("distance_km IS NULL OR distance_km >= 0", name="ck_cardio_activities_distance"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cardio_activities_user_id", "cardio_activities", ["user_id"])
    op.create_index("ix_cardio_activities_user_date", "cardio_activities", ["user_id", "activity_date"])

    op.create_table(
        "hybrid_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_type", sa.String(length=24), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint(
            "session_type IN ('hyrox_full', 'hyrox_half', 'hyrox_stations_only', 'custom')",
            name="ck_hybrid_sessions_type",
        ),
        sa.CheckConstraint(
            "total_duration_seconds IS NULL OR total_duration_seconds >= 0",
            name="ck_hybrid_sessions_duration",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hybrid_sessions_user_id", "hybrid_sessions", ["user_id"])
    op.create_index("ix_hybrid_sessions_user_started", "hybrid_sessions", ["user_id", "started_at"])

    op.create_table(
        "hybrid_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("segment_type", sa.String(length=8), nullable=False),
        sa.Column("segment_name", sa.String(length=160), nullable=False),
        sa.Column("station_key", sa.String(length=80), nullable=True),
        sa.Column("target_distance_m", sa.Integer(), nullable=True),
        sa.Column("target_reps", sa.Integer(), nullable=True),
        sa.Column("load", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("load_unit", sa.String(length=4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("position >= 0", name="ck_hybrid_segments_position"),
        sa.CheckConstraint("segment_type IN ('run', 'station')", name="ck_hybrid_segments_type"),
        sa.CheckConstraint(
            "target_distance_m IS NULL OR target_distance_m >= 0",
            name="ck_hybrid_segments_target_distance",
        ),
        sa.CheckConstraint("target_reps IS NULL OR target_reps >= 0", name="ck_hybrid_segments_target_reps"),
        sa.CheckConstraint("load IS NULL OR load >= 0", name="ck_hybrid_segments_load"),
        sa.CheckConstraint("load_unit IS NULL OR load_unit IN ('kg', 'lb')", name="ck_hybrid_segments_load_unit"),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_hybrid_segments_duration",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["hybrid_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hybrid_segments_user_id", "hybrid_segments", ["user_id"])
    op.create_index("ix_hybrid_segments_session_id", "hybrid_segments", ["session_id"])
    op.create_index("ix_hybrid_segments_session_position", "hybrid_segments", ["session_id", "position"])


def downgrade() -> None:
    op.drop_table("hybrid_segments")
    op.drop_table("hybrid_sessions")
    op.drop_table("cardio_activities")
