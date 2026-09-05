"""create nutrition tables

Revision ID: 0002_nutrition
Revises: 0001_users_profiles
Create Date: 2026-09-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_nutrition"
down_revision: Union[str, Sequence[str], None] = "0001_users_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrition_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("target_calories_kcal", sa.Numeric(8, 2), nullable=False),
        sa.Column("target_protein_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("target_carbs_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("target_fat_g", sa.Numeric(8, 2), nullable=False),
        sa.Column("target_fiber_g", sa.Numeric(8, 2), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.CheckConstraint("target_calories_kcal > 0", name="ck_nutrition_goals_calories_positive"),
        sa.CheckConstraint("target_protein_g >= 0", name="ck_nutrition_goals_protein_nonnegative"),
        sa.CheckConstraint("target_carbs_g >= 0", name="ck_nutrition_goals_carbs_nonnegative"),
        sa.CheckConstraint("target_fat_g >= 0", name="ck_nutrition_goals_fat_nonnegative"),
        sa.CheckConstraint("target_fiber_g IS NULL OR target_fiber_g >= 0", name="ck_nutrition_goals_fiber_nonnegative"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_goals_user_id", "nutrition_goals", ["user_id"], unique=True)

    op.create_table(
        "nutrition_foods",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("brand", sa.String(160), nullable=True),
        sa.Column("basis_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("basis_unit", sa.String(16), nullable=False),
        sa.Column("calories_kcal", sa.Numeric(10, 2), nullable=False),
        sa.Column("protein_g", sa.Numeric(10, 2), nullable=False),
        sa.Column("carbs_g", sa.Numeric(10, 2), nullable=False),
        sa.Column("fat_g", sa.Numeric(10, 2), nullable=False),
        sa.Column("fiber_g", sa.Numeric(10, 2), nullable=True),
        sa.Column("preparation_state", sa.String(16), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.CheckConstraint("basis_amount > 0", name="ck_nutrition_foods_basis_positive"),
        sa.CheckConstraint("basis_unit IN ('g', 'ml', 'piece', 'serving')", name="ck_nutrition_foods_basis_unit"),
        sa.CheckConstraint("calories_kcal >= 0", name="ck_nutrition_foods_calories_nonnegative"),
        sa.CheckConstraint("protein_g >= 0", name="ck_nutrition_foods_protein_nonnegative"),
        sa.CheckConstraint("carbs_g >= 0", name="ck_nutrition_foods_carbs_nonnegative"),
        sa.CheckConstraint("fat_g >= 0", name="ck_nutrition_foods_fat_nonnegative"),
        sa.CheckConstraint("fiber_g IS NULL OR fiber_g >= 0", name="ck_nutrition_foods_fiber_nonnegative"),
        sa.CheckConstraint("preparation_state IN ('unspecified', 'raw', 'cooked')", name="ck_nutrition_foods_preparation_state"),
        sa.CheckConstraint("source IN ('starter', 'custom', 'label')", name="ck_nutrition_foods_source"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_foods_user_id", "nutrition_foods", ["user_id"], unique=False)
    op.create_index("ix_nutrition_foods_user_name", "nutrition_foods", ["user_id", "name"], unique=False)

    op.create_table(
        "nutrition_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("logged_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False),
        sa.Column("source_food_id", sa.Uuid(), nullable=True),
        sa.Column("food_name_snapshot", sa.String(160), nullable=False),
        sa.Column("brand_snapshot", sa.String(160), nullable=True),
        sa.Column("preparation_state_snapshot", sa.String(16), nullable=False),
        sa.Column("calories_kcal_snapshot", sa.Numeric(10, 2), nullable=False),
        sa.Column("protein_g_snapshot", sa.Numeric(10, 2), nullable=False),
        sa.Column("carbs_g_snapshot", sa.Numeric(10, 2), nullable=False),
        sa.Column("fat_g_snapshot", sa.Numeric(10, 2), nullable=False),
        sa.Column("fiber_g_snapshot", sa.Numeric(10, 2), nullable=True),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.CheckConstraint("meal_type IN ('breakfast', 'lunch', 'dinner', 'snack', 'other')", name="ck_nutrition_entries_meal_type"),
        sa.CheckConstraint("amount > 0", name="ck_nutrition_entries_amount_positive"),
        sa.CheckConstraint("unit IN ('g', 'ml', 'piece', 'serving')", name="ck_nutrition_entries_unit"),
        sa.CheckConstraint("calories_kcal_snapshot >= 0", name="ck_nutrition_entries_calories_nonnegative"),
        sa.CheckConstraint("protein_g_snapshot >= 0", name="ck_nutrition_entries_protein_nonnegative"),
        sa.CheckConstraint("carbs_g_snapshot >= 0", name="ck_nutrition_entries_carbs_nonnegative"),
        sa.CheckConstraint("fat_g_snapshot >= 0", name="ck_nutrition_entries_fat_nonnegative"),
        sa.CheckConstraint("fiber_g_snapshot IS NULL OR fiber_g_snapshot >= 0", name="ck_nutrition_entries_fiber_nonnegative"),
        sa.CheckConstraint("preparation_state_snapshot IN ('unspecified', 'raw', 'cooked')", name="ck_nutrition_entries_preparation_state"),
        sa.ForeignKeyConstraint(["source_food_id"], ["nutrition_foods.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_entries_user_id", "nutrition_entries", ["user_id"], unique=False)
    op.create_index("ix_nutrition_entries_logged_date", "nutrition_entries", ["logged_date"], unique=False)
    op.create_index("ix_nutrition_entries_user_date", "nutrition_entries", ["user_id", "logged_date"], unique=False)

    op.create_table(
        "nutrition_saved_meals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_saved_meals_user_id", "nutrition_saved_meals", ["user_id"], unique=False)

    op.create_table(
        "nutrition_saved_meal_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("meal_id", sa.Uuid(), nullable=False),
        sa.Column("food_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(16), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("client_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_nutrition_saved_meal_items_amount_positive"),
        sa.CheckConstraint("unit IN ('g', 'ml', 'piece', 'serving')", name="ck_nutrition_saved_meal_items_unit"),
        sa.CheckConstraint("position >= 0", name="ck_nutrition_saved_meal_items_position_nonnegative"),
        sa.ForeignKeyConstraint(["food_id"], ["nutrition_foods.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["meal_id"], ["nutrition_saved_meals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["pace_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_saved_meal_items_user_id", "nutrition_saved_meal_items", ["user_id"], unique=False)
    op.create_index("ix_nutrition_saved_meal_items_meal_id", "nutrition_saved_meal_items", ["meal_id"], unique=False)
    op.create_index("ix_nutrition_saved_meal_items_food_id", "nutrition_saved_meal_items", ["food_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_nutrition_saved_meal_items_food_id", table_name="nutrition_saved_meal_items")
    op.drop_index("ix_nutrition_saved_meal_items_meal_id", table_name="nutrition_saved_meal_items")
    op.drop_index("ix_nutrition_saved_meal_items_user_id", table_name="nutrition_saved_meal_items")
    op.drop_table("nutrition_saved_meal_items")
    op.drop_index("ix_nutrition_saved_meals_user_id", table_name="nutrition_saved_meals")
    op.drop_table("nutrition_saved_meals")
    op.drop_index("ix_nutrition_entries_user_date", table_name="nutrition_entries")
    op.drop_index("ix_nutrition_entries_logged_date", table_name="nutrition_entries")
    op.drop_index("ix_nutrition_entries_user_id", table_name="nutrition_entries")
    op.drop_table("nutrition_entries")
    op.drop_index("ix_nutrition_foods_user_name", table_name="nutrition_foods")
    op.drop_index("ix_nutrition_foods_user_id", table_name="nutrition_foods")
    op.drop_table("nutrition_foods")
    op.drop_index("ix_nutrition_goals_user_id", table_name="nutrition_goals")
    op.drop_table("nutrition_goals")
