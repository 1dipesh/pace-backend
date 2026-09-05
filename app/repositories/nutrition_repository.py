from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.nutrition import (
    NutritionEntry,
    NutritionFood,
    NutritionGoal,
    NutritionSavedMeal,
    NutritionSavedMealItem,
)


def get_goals(db: Session, user_id: UUID, *, include_deleted: bool = False) -> NutritionGoal | None:
    stmt = select(NutritionGoal).where(NutritionGoal.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(NutritionGoal.deleted_at.is_(None))
    return db.scalar(stmt)


def save_goals(db: Session, user_id: UUID, values: dict) -> NutritionGoal:
    goals = get_goals(db, user_id, include_deleted=True)
    if goals is None:
        goals = NutritionGoal(user_id=user_id, **values)
        db.add(goals)
    else:
        for field, value in values.items():
            setattr(goals, field, value)
        goals.deleted_at = None
        goals.version += 1
    db.commit()
    db.refresh(goals)
    return goals


def create_food(db: Session, user_id: UUID, values: dict) -> NutritionFood:
    food = NutritionFood(user_id=user_id, **values)
    db.add(food)
    db.commit()
    db.refresh(food)
    return food


def list_foods(db: Session, user_id: UUID, *, favorite_only: bool = False) -> list[NutritionFood]:
    stmt = (
        select(NutritionFood)
        .where(NutritionFood.user_id == user_id, NutritionFood.deleted_at.is_(None))
        .order_by(NutritionFood.name.asc(), NutritionFood.created_at.asc())
    )
    if favorite_only:
        stmt = stmt.where(NutritionFood.is_favorite.is_(True))
    return list(db.scalars(stmt).all())


def get_food(
    db: Session, user_id: UUID, food_id: UUID, *, include_deleted: bool = False
) -> NutritionFood | None:
    stmt = select(NutritionFood).where(
        NutritionFood.id == food_id,
        NutritionFood.user_id == user_id,
    )
    if not include_deleted:
        stmt = stmt.where(NutritionFood.deleted_at.is_(None))
    return db.scalar(stmt)


def update_food(db: Session, food: NutritionFood, values: dict) -> NutritionFood:
    for field, value in values.items():
        setattr(food, field, value)
    food.version += 1
    db.commit()
    db.refresh(food)
    return food


def soft_delete_food(db: Session, food: NutritionFood) -> None:
    food.deleted_at = datetime.now(timezone.utc)
    food.version += 1
    db.commit()


def create_entry(db: Session, entry: NutritionEntry, *, commit: bool = True) -> NutritionEntry:
    db.add(entry)
    if commit:
        db.commit()
        db.refresh(entry)
    else:
        db.flush()
    return entry


def get_entry(db: Session, user_id: UUID, entry_id: UUID) -> NutritionEntry | None:
    return db.scalar(
        select(NutritionEntry).where(
            NutritionEntry.id == entry_id,
            NutritionEntry.user_id == user_id,
            NutritionEntry.deleted_at.is_(None),
        )
    )


def list_entries(
    db: Session,
    user_id: UUID,
    *,
    logged_date: date | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[NutritionEntry]:
    stmt = select(NutritionEntry).where(
        NutritionEntry.user_id == user_id,
        NutritionEntry.deleted_at.is_(None),
    )
    if logged_date is not None:
        stmt = stmt.where(NutritionEntry.logged_date == logged_date)
    else:
        if start_date is not None:
            stmt = stmt.where(NutritionEntry.logged_date >= start_date)
        if end_date is not None:
            stmt = stmt.where(NutritionEntry.logged_date <= end_date)
    stmt = stmt.order_by(NutritionEntry.logged_date.desc(), NutritionEntry.created_at.desc())
    return list(db.scalars(stmt).all())


def update_entry(db: Session, entry: NutritionEntry, values: dict) -> NutritionEntry:
    for field, value in values.items():
        setattr(entry, field, value)
    entry.version += 1
    db.commit()
    db.refresh(entry)
    return entry


def soft_delete_entry(db: Session, entry: NutritionEntry) -> None:
    entry.deleted_at = datetime.now(timezone.utc)
    entry.version += 1
    db.commit()


def create_saved_meal(
    db: Session,
    user_id: UUID,
    *,
    name: str,
    client_updated_at,
    items: list[dict],
) -> NutritionSavedMeal:
    meal = NutritionSavedMeal(
        user_id=user_id,
        name=name,
        client_updated_at=client_updated_at,
    )
    db.add(meal)
    db.flush()

    for position, values in enumerate(items):
        db.add(
            NutritionSavedMealItem(
                user_id=user_id,
                meal_id=meal.id,
                position=position,
                **values,
            )
        )
    db.commit()
    db.refresh(meal)
    return meal


def list_saved_meals(db: Session, user_id: UUID) -> list[NutritionSavedMeal]:
    return list(
        db.scalars(
            select(NutritionSavedMeal)
            .where(
                NutritionSavedMeal.user_id == user_id,
                NutritionSavedMeal.deleted_at.is_(None),
            )
            .order_by(NutritionSavedMeal.name.asc(), NutritionSavedMeal.created_at.asc())
        ).all()
    )


def get_saved_meal(db: Session, user_id: UUID, meal_id: UUID) -> NutritionSavedMeal | None:
    return db.scalar(
        select(NutritionSavedMeal).where(
            NutritionSavedMeal.id == meal_id,
            NutritionSavedMeal.user_id == user_id,
            NutritionSavedMeal.deleted_at.is_(None),
        )
    )


def list_saved_meal_items(
    db: Session, user_id: UUID, meal_id: UUID, *, include_deleted: bool = False
) -> list[NutritionSavedMealItem]:
    stmt = select(NutritionSavedMealItem).where(
        NutritionSavedMealItem.user_id == user_id,
        NutritionSavedMealItem.meal_id == meal_id,
    )
    if not include_deleted:
        stmt = stmt.where(NutritionSavedMealItem.deleted_at.is_(None))
    stmt = stmt.order_by(NutritionSavedMealItem.position.asc())
    return list(db.scalars(stmt).all())


def update_saved_meal(
    db: Session,
    meal: NutritionSavedMeal,
    *,
    name: str | None,
    replace_items: list[dict] | None,
    client_updated_at,
) -> NutritionSavedMeal:
    if name is not None:
        meal.name = name
    if client_updated_at is not None:
        meal.client_updated_at = client_updated_at

    if replace_items is not None:
        now = datetime.now(timezone.utc)
        for item in list_saved_meal_items(db, meal.user_id, meal.id):
            item.deleted_at = now
            item.version += 1
        for position, values in enumerate(replace_items):
            db.add(
                NutritionSavedMealItem(
                    user_id=meal.user_id,
                    meal_id=meal.id,
                    position=position,
                    **values,
                )
            )

    meal.version += 1
    db.commit()
    db.refresh(meal)
    return meal


def soft_delete_saved_meal(db: Session, meal: NutritionSavedMeal) -> None:
    now = datetime.now(timezone.utc)
    meal.deleted_at = now
    meal.version += 1
    for item in list_saved_meal_items(db, meal.user_id, meal.id):
        item.deleted_at = now
        item.version += 1
    db.commit()
