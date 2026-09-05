from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.nutrition import NutritionEntry, NutritionFood, NutritionGoal, NutritionSavedMeal
from app.models.user import PaceUser
from app.repositories import nutrition_repository as repo
from app.schemas.nutrition import (
    NutritionDailySummary,
    NutritionEntryCreate,
    NutritionEntryResponse,
    NutritionEntryUpdate,
    NutritionFoodCreate,
    NutritionFoodResponse,
    NutritionFoodUpdate,
    NutritionGoalsResponse,
    NutritionGoalsUpsert,
    NutritionTotals,
    SavedMealCreate,
    SavedMealLogRequest,
    SavedMealResponse,
    SavedMealItemResponse,
    SavedMealUpdate,
)

TWO_DP = Decimal("0.01")


def D(value) -> Decimal:
    return Decimal(str(value))


def q(value: Decimal) -> Decimal:
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def scaled_nutrition(food: NutritionFood, amount) -> dict[str, Decimal | None]:
    multiplier = D(amount) / food.basis_amount
    return {
        "calories_kcal": q(food.calories_kcal * multiplier),
        "protein_g": q(food.protein_g * multiplier),
        "carbs_g": q(food.carbs_g * multiplier),
        "fat_g": q(food.fat_g * multiplier),
        "fiber_g": q(food.fiber_g * multiplier) if food.fiber_g is not None else None,
    }


def goals_to_response(goals: NutritionGoal) -> NutritionGoalsResponse:
    return NutritionGoalsResponse.model_validate(goals)


def get_goals(db: Session, user: PaceUser) -> NutritionGoalsResponse:
    goals = repo.get_goals(db, user.id)
    if goals is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutrition goals not found")
    return goals_to_response(goals)


def upsert_goals(db: Session, user: PaceUser, payload: NutritionGoalsUpsert) -> NutritionGoalsResponse:
    goals = repo.save_goals(db, user.id, payload.model_dump())
    return goals_to_response(goals)


def food_to_response(food: NutritionFood) -> NutritionFoodResponse:
    return NutritionFoodResponse.model_validate(food)


def create_food(db: Session, user: PaceUser, payload: NutritionFoodCreate) -> NutritionFoodResponse:
    return food_to_response(repo.create_food(db, user.id, payload.model_dump()))


def list_foods(db: Session, user: PaceUser, favorite_only: bool) -> list[NutritionFoodResponse]:
    return [food_to_response(food) for food in repo.list_foods(db, user.id, favorite_only=favorite_only)]


def require_food(db: Session, user: PaceUser, food_id: UUID, *, include_deleted: bool = False) -> NutritionFood:
    food = repo.get_food(db, user.id, food_id, include_deleted=include_deleted)
    if food is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
    return food


def get_food(db: Session, user: PaceUser, food_id: UUID) -> NutritionFoodResponse:
    return food_to_response(require_food(db, user, food_id))


def update_food(
    db: Session, user: PaceUser, food_id: UUID, payload: NutritionFoodUpdate
) -> NutritionFoodResponse:
    food = require_food(db, user, food_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return food_to_response(food)
    return food_to_response(repo.update_food(db, food, changes))


def delete_food(db: Session, user: PaceUser, food_id: UUID) -> None:
    food = require_food(db, user, food_id)
    repo.soft_delete_food(db, food)


def entry_to_response(entry: NutritionEntry) -> NutritionEntryResponse:
    return NutritionEntryResponse(
        id=entry.id,
        user_id=entry.user_id,
        logged_date=entry.logged_date,
        meal_type=entry.meal_type,
        amount=entry.amount,
        unit=entry.unit,
        source_food_id=entry.source_food_id,
        food_name=entry.food_name_snapshot,
        brand=entry.brand_snapshot,
        preparation_state=entry.preparation_state_snapshot,
        calories_kcal=entry.calories_kcal_snapshot,
        protein_g=entry.protein_g_snapshot,
        carbs_g=entry.carbs_g_snapshot,
        fat_g=entry.fat_g_snapshot,
        fiber_g=entry.fiber_g_snapshot,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        deleted_at=entry.deleted_at,
        client_updated_at=entry.client_updated_at,
        version=entry.version,
    )


def build_entry_from_food(
    *,
    user_id,
    food: NutritionFood,
    logged_date,
    meal_type,
    amount,
    unit,
    client_updated_at=None,
) -> NutritionEntry:
    if unit != food.basis_unit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unit must match the food basis unit '{food.basis_unit}'",
        )
    nutrition = scaled_nutrition(food, amount)
    return NutritionEntry(
        user_id=user_id,
        logged_date=logged_date,
        meal_type=meal_type,
        amount=D(amount),
        unit=unit,
        source_food_id=food.id,
        food_name_snapshot=food.name,
        brand_snapshot=food.brand,
        preparation_state_snapshot=food.preparation_state,
        calories_kcal_snapshot=nutrition["calories_kcal"],
        protein_g_snapshot=nutrition["protein_g"],
        carbs_g_snapshot=nutrition["carbs_g"],
        fat_g_snapshot=nutrition["fat_g"],
        fiber_g_snapshot=nutrition["fiber_g"],
        client_updated_at=client_updated_at,
    )


def create_entry(db: Session, user: PaceUser, payload: NutritionEntryCreate) -> NutritionEntryResponse:
    if payload.food_id is not None:
        food = require_food(db, user, payload.food_id)
        entry = build_entry_from_food(
            user_id=user.id,
            food=food,
            logged_date=payload.logged_date,
            meal_type=payload.meal_type,
            amount=payload.amount,
            unit=payload.unit,
            client_updated_at=payload.client_updated_at,
        )
    else:
        manual = payload.manual
        assert manual is not None
        entry = NutritionEntry(
            user_id=user.id,
            logged_date=payload.logged_date,
            meal_type=payload.meal_type,
            amount=D(manual.amount),
            unit=manual.unit,
            source_food_id=None,
            food_name_snapshot=manual.name,
            brand_snapshot=manual.brand,
            preparation_state_snapshot=manual.preparation_state,
            calories_kcal_snapshot=D(manual.calories_kcal),
            protein_g_snapshot=D(manual.protein_g),
            carbs_g_snapshot=D(manual.carbs_g),
            fat_g_snapshot=D(manual.fat_g),
            fiber_g_snapshot=D(manual.fiber_g) if manual.fiber_g is not None else None,
            client_updated_at=payload.client_updated_at,
        )
    return entry_to_response(repo.create_entry(db, entry))


def list_entries(
    db: Session,
    user: PaceUser,
    *,
    logged_date=None,
    start_date=None,
    end_date=None,
) -> list[NutritionEntryResponse]:
    if logged_date is not None and (start_date is not None or end_date is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use logged_date or a date range, not both",
        )
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date cannot be after end_date",
        )
    return [
        entry_to_response(entry)
        for entry in repo.list_entries(
            db,
            user.id,
            logged_date=logged_date,
            start_date=start_date,
            end_date=end_date,
        )
    ]


def require_entry(db: Session, user: PaceUser, entry_id: UUID) -> NutritionEntry:
    entry = repo.get_entry(db, user.id, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nutrition entry not found")
    return entry


def get_entry(db: Session, user: PaceUser, entry_id: UUID) -> NutritionEntryResponse:
    return entry_to_response(require_entry(db, user, entry_id))


def update_entry(
    db: Session, user: PaceUser, entry_id: UUID, payload: NutritionEntryUpdate
) -> NutritionEntryResponse:
    entry = require_entry(db, user, entry_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return entry_to_response(entry)

    if "amount" in changes:
        old_amount = entry.amount
        new_amount = D(changes["amount"])
        multiplier = new_amount / old_amount
        for field in (
            "calories_kcal_snapshot",
            "protein_g_snapshot",
            "carbs_g_snapshot",
            "fat_g_snapshot",
        ):
            setattr(entry, field, q(getattr(entry, field) * multiplier))
        if entry.fiber_g_snapshot is not None:
            entry.fiber_g_snapshot = q(entry.fiber_g_snapshot * multiplier)
        changes["amount"] = new_amount

    return entry_to_response(repo.update_entry(db, entry, changes))


def delete_entry(db: Session, user: PaceUser, entry_id: UUID) -> None:
    repo.soft_delete_entry(db, require_entry(db, user, entry_id))


def totals_for_entries(entries: list[NutritionEntryResponse]) -> NutritionTotals:
    fiber_values = [D(entry.fiber_g) for entry in entries if entry.fiber_g is not None]
    return NutritionTotals(
        calories_kcal=float(sum((D(entry.calories_kcal) for entry in entries), Decimal("0"))),
        protein_g=float(sum((D(entry.protein_g) for entry in entries), Decimal("0"))),
        carbs_g=float(sum((D(entry.carbs_g) for entry in entries), Decimal("0"))),
        fat_g=float(sum((D(entry.fat_g) for entry in entries), Decimal("0"))),
        fiber_g=float(sum(fiber_values, Decimal("0"))) if fiber_values else None,
    )


def daily_summary(db: Session, user: PaceUser, logged_date) -> NutritionDailySummary:
    entries = list_entries(db, user, logged_date=logged_date)
    goals = repo.get_goals(db, user.id)
    return NutritionDailySummary(
        logged_date=logged_date,
        totals=totals_for_entries(entries),
        goals=goals_to_response(goals) if goals is not None else None,
        entries=entries,
    )


def validate_saved_meal_items(db: Session, user: PaceUser, items) -> list[dict]:
    validated: list[dict] = []
    for item in items:
        food = require_food(db, user, item.food_id)
        if item.unit != food.basis_unit:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unit for '{food.name}' must match '{food.basis_unit}'",
            )
        validated.append({"food_id": food.id, "amount": D(item.amount), "unit": item.unit})
    return validated


def saved_meal_to_response(db: Session, user: PaceUser, meal: NutritionSavedMeal) -> SavedMealResponse:
    items_response: list[SavedMealItemResponse] = []
    item_totals: list[NutritionTotals] = []
    for item in repo.list_saved_meal_items(db, user.id, meal.id):
        food = require_food(db, user, item.food_id, include_deleted=True)
        nutrition = scaled_nutrition(food, item.amount)
        item_totals.append(
            NutritionTotals(
                calories_kcal=nutrition["calories_kcal"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fat_g"],
                fiber_g=nutrition["fiber_g"],
            )
        )
        items_response.append(
            SavedMealItemResponse(
                id=item.id,
                user_id=item.user_id,
                meal_id=item.meal_id,
                food_id=item.food_id,
                amount=item.amount,
                unit=item.unit,
                position=item.position,
                food_name=food.name,
                brand=food.brand,
                food_deleted=food.deleted_at is not None,
                calories_kcal=nutrition["calories_kcal"],
                protein_g=nutrition["protein_g"],
                carbs_g=nutrition["carbs_g"],
                fat_g=nutrition["fat_g"],
                fiber_g=nutrition["fiber_g"],
                created_at=item.created_at,
                updated_at=item.updated_at,
                deleted_at=item.deleted_at,
                client_updated_at=item.client_updated_at,
                version=item.version,
            )
        )

    totals = NutritionTotals(
        calories_kcal=sum((D(t.calories_kcal) for t in item_totals), Decimal("0")),
        protein_g=sum((D(t.protein_g) for t in item_totals), Decimal("0")),
        carbs_g=sum((D(t.carbs_g) for t in item_totals), Decimal("0")),
        fat_g=sum((D(t.fat_g) for t in item_totals), Decimal("0")),
        fiber_g=(
            sum((D(t.fiber_g) for t in item_totals if t.fiber_g is not None), Decimal("0"))
            if any(t.fiber_g is not None for t in item_totals)
            else None
        ),
    )
    return SavedMealResponse(
        id=meal.id,
        user_id=meal.user_id,
        name=meal.name,
        items=items_response,
        totals=totals,
        created_at=meal.created_at,
        updated_at=meal.updated_at,
        deleted_at=meal.deleted_at,
        client_updated_at=meal.client_updated_at,
        version=meal.version,
    )


def create_saved_meal(
    db: Session, user: PaceUser, payload: SavedMealCreate
) -> SavedMealResponse:
    items = validate_saved_meal_items(db, user, payload.items)
    meal = repo.create_saved_meal(
        db,
        user.id,
        name=payload.name,
        client_updated_at=payload.client_updated_at,
        items=items,
    )
    return saved_meal_to_response(db, user, meal)


def list_saved_meals(db: Session, user: PaceUser) -> list[SavedMealResponse]:
    return [saved_meal_to_response(db, user, meal) for meal in repo.list_saved_meals(db, user.id)]


def require_saved_meal(db: Session, user: PaceUser, meal_id: UUID) -> NutritionSavedMeal:
    meal = repo.get_saved_meal(db, user.id, meal_id)
    if meal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved meal not found")
    return meal


def get_saved_meal(db: Session, user: PaceUser, meal_id: UUID) -> SavedMealResponse:
    return saved_meal_to_response(db, user, require_saved_meal(db, user, meal_id))


def update_saved_meal(
    db: Session, user: PaceUser, meal_id: UUID, payload: SavedMealUpdate
) -> SavedMealResponse:
    meal = require_saved_meal(db, user, meal_id)
    if not payload.model_fields_set:
        return saved_meal_to_response(db, user, meal)
    items = None
    if payload.items is not None:
        items = validate_saved_meal_items(db, user, payload.items)
    meal = repo.update_saved_meal(
        db,
        meal,
        name=payload.name if "name" in payload.model_fields_set else None,
        replace_items=items,
        client_updated_at=payload.client_updated_at,
    )
    return saved_meal_to_response(db, user, meal)


def delete_saved_meal(db: Session, user: PaceUser, meal_id: UUID) -> None:
    repo.soft_delete_saved_meal(db, require_saved_meal(db, user, meal_id))


def log_saved_meal(
    db: Session, user: PaceUser, meal_id: UUID, payload: SavedMealLogRequest
) -> list[NutritionEntryResponse]:
    meal = require_saved_meal(db, user, meal_id)
    items = repo.list_saved_meal_items(db, user.id, meal.id)
    if not items:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Saved meal has no items")

    entries: list[NutritionEntry] = []
    for item in items:
        food = require_food(db, user, item.food_id, include_deleted=True)
        if food.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Saved meal contains deleted food '{food.name}'. Update the saved meal first.",
            )
        if item.unit != food.basis_unit:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Saved meal unit for '{food.name}' no longer matches the food definition",
            )
        entry = build_entry_from_food(
            user_id=user.id,
            food=food,
            logged_date=payload.logged_date,
            meal_type=payload.meal_type,
            amount=item.amount,
            unit=item.unit,
            client_updated_at=payload.client_updated_at,
        )
        repo.create_entry(db, entry, commit=False)
        entries.append(entry)

    db.commit()
    for entry in entries:
        db.refresh(entry)
    return [entry_to_response(entry) for entry in entries]
