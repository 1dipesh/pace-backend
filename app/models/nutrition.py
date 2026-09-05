import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


NUTRITION_UNITS = "('g', 'ml', 'piece', 'serving')"
MEAL_TYPES = "('breakfast', 'lunch', 'dinner', 'snack', 'other')"
PREPARATION_STATES = "('unspecified', 'raw', 'cooked')"
FOOD_SOURCES = "('starter', 'custom', 'label')"


class NutritionGoal(TimestampMixin, Base):
    __tablename__ = "nutrition_goals"
    __table_args__ = (
        CheckConstraint("target_calories_kcal > 0", name="ck_nutrition_goals_calories_positive"),
        CheckConstraint("target_protein_g >= 0", name="ck_nutrition_goals_protein_nonnegative"),
        CheckConstraint("target_carbs_g >= 0", name="ck_nutrition_goals_carbs_nonnegative"),
        CheckConstraint("target_fat_g >= 0", name="ck_nutrition_goals_fat_nonnegative"),
        CheckConstraint(
            "target_fiber_g IS NULL OR target_fiber_g >= 0",
            name="ck_nutrition_goals_fiber_nonnegative",
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
    target_calories_kcal: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    target_protein_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    target_carbs_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    target_fat_g: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    target_fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NutritionFood(TimestampMixin, Base):
    __tablename__ = "nutrition_foods"
    __table_args__ = (
        CheckConstraint("basis_amount > 0", name="ck_nutrition_foods_basis_positive"),
        CheckConstraint(f"basis_unit IN {NUTRITION_UNITS}", name="ck_nutrition_foods_basis_unit"),
        CheckConstraint("calories_kcal >= 0", name="ck_nutrition_foods_calories_nonnegative"),
        CheckConstraint("protein_g >= 0", name="ck_nutrition_foods_protein_nonnegative"),
        CheckConstraint("carbs_g >= 0", name="ck_nutrition_foods_carbs_nonnegative"),
        CheckConstraint("fat_g >= 0", name="ck_nutrition_foods_fat_nonnegative"),
        CheckConstraint("fiber_g IS NULL OR fiber_g >= 0", name="ck_nutrition_foods_fiber_nonnegative"),
        CheckConstraint(
            f"preparation_state IN {PREPARATION_STATES}",
            name="ck_nutrition_foods_preparation_state",
        ),
        CheckConstraint(f"source IN {FOOD_SOURCES}", name="ck_nutrition_foods_source"),
        Index("ix_nutrition_foods_user_name", "user_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    basis_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    basis_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    calories_kcal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    preparation_state: Mapped[str] = mapped_column(String(16), default="unspecified", nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="custom", nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NutritionEntry(TimestampMixin, Base):
    __tablename__ = "nutrition_entries"
    __table_args__ = (
        CheckConstraint(f"meal_type IN {MEAL_TYPES}", name="ck_nutrition_entries_meal_type"),
        CheckConstraint("amount > 0", name="ck_nutrition_entries_amount_positive"),
        CheckConstraint(f"unit IN {NUTRITION_UNITS}", name="ck_nutrition_entries_unit"),
        CheckConstraint("calories_kcal_snapshot >= 0", name="ck_nutrition_entries_calories_nonnegative"),
        CheckConstraint("protein_g_snapshot >= 0", name="ck_nutrition_entries_protein_nonnegative"),
        CheckConstraint("carbs_g_snapshot >= 0", name="ck_nutrition_entries_carbs_nonnegative"),
        CheckConstraint("fat_g_snapshot >= 0", name="ck_nutrition_entries_fat_nonnegative"),
        CheckConstraint(
            "fiber_g_snapshot IS NULL OR fiber_g_snapshot >= 0",
            name="ck_nutrition_entries_fiber_nonnegative",
        ),
        CheckConstraint(
            f"preparation_state_snapshot IN {PREPARATION_STATES}",
            name="ck_nutrition_entries_preparation_state",
        ),
        Index("ix_nutrition_entries_user_date", "user_id", "logged_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    logged_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    source_food_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("nutrition_foods.id", ondelete="SET NULL"), nullable=True
    )
    food_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    brand_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    preparation_state_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    calories_kcal_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein_g_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbs_g_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fat_g_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fiber_g_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NutritionSavedMeal(TimestampMixin, Base):
    __tablename__ = "nutrition_saved_meals"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NutritionSavedMealItem(TimestampMixin, Base):
    __tablename__ = "nutrition_saved_meal_items"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_nutrition_saved_meal_items_amount_positive"),
        CheckConstraint(f"unit IN {NUTRITION_UNITS}", name="ck_nutrition_saved_meal_items_unit"),
        CheckConstraint("position >= 0", name="ck_nutrition_saved_meal_items_position_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    meal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("nutrition_saved_meals.id", ondelete="CASCADE"), index=True, nullable=False
    )
    food_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("nutrition_foods.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
