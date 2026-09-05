"""create pace users and profiles

Revision ID: 0001_users_profiles
Revises:
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_users_profiles"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pace_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("auth_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pace_users_auth_subject", "pace_users", ["auth_subject"], unique=True)

    op.create_table(
        "pace_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("height_cm", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("calorie_estimate_sex", sa.String(length=16), nullable=False),
        sa.Column("goal", sa.String(length=32), nullable=False),
        sa.Column("activity_level", sa.String(length=32), nullable=False),
        sa.Column("training_experience", sa.String(length=32), nullable=False),
        sa.Column("training_days_per_week", sa.SmallInteger(), nullable=False),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.CheckConstraint("activity_level IN ('mostly_sedentary', 'lightly_active', 'active', 'very_active')", name="ck_pace_profiles_activity_level"),
        sa.CheckConstraint("calorie_estimate_sex IN ('male', 'female', 'neutral')", name="ck_pace_profiles_calorie_estimate_sex"),
        sa.CheckConstraint("goal IN ('lose_body_fat', 'maintain', 'build_muscle', 'improve_performance', 'general_health')", name="ck_pace_profiles_goal"),
        sa.CheckConstraint("height_cm > 0", name="ck_pace_profiles_height_positive"),
        sa.CheckConstraint("training_days_per_week >= 0 AND training_days_per_week <= 6", name="ck_pace_profiles_training_days_range"),
        sa.CheckConstraint("training_experience IN ('beginner', 'intermediate', 'experienced')", name="ck_pace_profiles_training_experience"),
        sa.CheckConstraint("weight_kg > 0", name="ck_pace_profiles_weight_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pace_profiles_user_id", "pace_profiles", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_pace_profiles_user_id", table_name="pace_profiles")
    op.drop_table("pace_profiles")
    op.drop_index("ix_pace_users_auth_subject", table_name="pace_users")
    op.drop_table("pace_users")
