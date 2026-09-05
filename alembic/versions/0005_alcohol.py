"""create alcohol tracking tables

Revision ID: 0005_alcohol
Revises: 0004_cardio_hybrid
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_alcohol"
down_revision: Union[str, Sequence[str], None] = "0004_cardio_hybrid"
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
        "alcohol_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("entry_mode", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_paused_seconds", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("entry_mode IN ('live', 'historical')", name="ck_alcohol_sessions_entry_mode"),
        sa.CheckConstraint("status IN ('active', 'completed')", name="ck_alcohol_sessions_status"),
        sa.CheckConstraint("total_paused_seconds >= 0", name="ck_alcohol_sessions_paused_nonnegative"),
        sa.CheckConstraint(
            "(entry_mode = 'live' AND started_at IS NOT NULL) OR "
            "(entry_mode = 'historical' AND started_at IS NULL AND status = 'completed')",
            name="ck_alcohol_sessions_mode_timing",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alcohol_sessions_user_id", "alcohol_sessions", ["user_id"])
    op.create_index("ix_alcohol_sessions_user_date", "alcohol_sessions", ["user_id", "session_date"])
    op.create_index("ix_alcohol_sessions_user_status", "alcohol_sessions", ["user_id", "status"])

    op.create_table(
        "alcohol_drinks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand", sa.String(length=160), nullable=True),
        sa.Column("volume_ml", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("abv_percent", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("alcohol_grams", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint(
            "category IN ('beer', 'wine', 'spirits', 'cocktail', 'other')",
            name="ck_alcohol_drinks_category",
        ),
        sa.CheckConstraint("volume_ml > 0", name="ck_alcohol_drinks_volume_positive"),
        sa.CheckConstraint("abv_percent >= 0 AND abv_percent <= 100", name="ck_alcohol_drinks_abv_range"),
        sa.CheckConstraint("alcohol_grams >= 0", name="ck_alcohol_drinks_grams_nonnegative"),
        sa.ForeignKeyConstraint(["session_id"], ["alcohol_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alcohol_drinks_user_id", "alcohol_drinks", ["user_id"])
    op.create_index("ix_alcohol_drinks_session_id", "alcohol_drinks", ["session_id"])
    op.create_index("ix_alcohol_drinks_session_logged", "alcohol_drinks", ["session_id", "logged_at"])

    op.create_table(
        "alcohol_water_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("volume_ml", sa.Integer(), nullable=True),
        sa.Column("container", sa.String(length=80), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("volume_ml IS NULL OR volume_ml > 0", name="ck_alcohol_water_entries_volume_positive"),
        sa.ForeignKeyConstraint(["session_id"], ["alcohol_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alcohol_water_entries_user_id", "alcohol_water_entries", ["user_id"])
    op.create_index("ix_alcohol_water_entries_session_id", "alcohol_water_entries", ["session_id"])
    op.create_index(
        "ix_alcohol_water_entries_session_logged",
        "alcohol_water_entries",
        ["session_id", "logged_at"],
    )

    op.create_table(
        "alcohol_favorites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("brand", sa.String(length=160), nullable=True),
        sa.Column("volume_ml", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("abv_percent", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint(
            "category IN ('beer', 'wine', 'spirits', 'cocktail', 'other')",
            name="ck_alcohol_favorites_category",
        ),
        sa.CheckConstraint("volume_ml > 0", name="ck_alcohol_favorites_volume_positive"),
        sa.CheckConstraint("abv_percent >= 0 AND abv_percent <= 100", name="ck_alcohol_favorites_abv_range"),
        sa.CheckConstraint("usage_count >= 0", name="ck_alcohol_favorites_usage_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alcohol_favorites_user_id", "alcohol_favorites", ["user_id"])
    op.create_index("ix_alcohol_favorites_user_name", "alcohol_favorites", ["user_id", "name"])

    op.create_table(
        "alcohol_breaks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("planned_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=12), server_default="running", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interrupted_by_drink_id", sa.Uuid(), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        *_sync_columns(),
        sa.CheckConstraint("planned_duration_seconds > 0", name="ck_alcohol_breaks_duration_positive"),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'interrupted', 'cancelled')",
            name="ck_alcohol_breaks_status",
        ),
        sa.ForeignKeyConstraint(["interrupted_by_drink_id"], ["alcohol_drinks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["alcohol_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alcohol_breaks_user_id", "alcohol_breaks", ["user_id"])
    op.create_index("ix_alcohol_breaks_session_id", "alcohol_breaks", ["session_id"])
    op.create_index("ix_alcohol_breaks_interrupted_by_drink_id", "alcohol_breaks", ["interrupted_by_drink_id"])
    op.create_index("ix_alcohol_breaks_session_started", "alcohol_breaks", ["session_id", "started_at"])


def downgrade() -> None:
    op.drop_table("alcohol_breaks")
    op.drop_table("alcohol_favorites")
    op.drop_table("alcohol_water_entries")
    op.drop_table("alcohol_drinks")
    op.drop_table("alcohol_sessions")
