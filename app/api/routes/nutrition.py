from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
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
    SavedMealCreate,
    SavedMealLogRequest,
    SavedMealResponse,
    SavedMealUpdate,
)
from app.services import nutrition_service

router = APIRouter(prefix="/api/v1/nutrition", tags=["nutrition"])


@router.get("/goals", response_model=NutritionGoalsResponse)
def get_goals(
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.get_goals(db, user)


@router.put("/goals", response_model=NutritionGoalsResponse)
def upsert_goals(
    payload: NutritionGoalsUpsert,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.upsert_goals(db, user, payload)


@router.post("/foods", response_model=NutritionFoodResponse, status_code=status.HTTP_201_CREATED)
def create_food(
    payload: NutritionFoodCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.create_food(db, user, payload)


@router.get("/foods", response_model=list[NutritionFoodResponse])
def list_foods(
    favorite_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.list_foods(db, user, favorite_only)


@router.get("/foods/{food_id}", response_model=NutritionFoodResponse)
def get_food(
    food_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.get_food(db, user, food_id)


@router.patch("/foods/{food_id}", response_model=NutritionFoodResponse)
def update_food(
    food_id: UUID,
    payload: NutritionFoodUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.update_food(db, user, food_id, payload)


@router.delete("/foods/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food(
    food_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    nutrition_service.delete_food(db, user, food_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/entries", response_model=NutritionEntryResponse, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: NutritionEntryCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.create_entry(db, user, payload)


@router.get("/entries", response_model=list[NutritionEntryResponse])
def list_entries(
    logged_date: date | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.list_entries(
        db,
        user,
        logged_date=logged_date,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/entries/{entry_id}", response_model=NutritionEntryResponse)
def get_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.get_entry(db, user, entry_id)


@router.patch("/entries/{entry_id}", response_model=NutritionEntryResponse)
def update_entry(
    entry_id: UUID,
    payload: NutritionEntryUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.update_entry(db, user, entry_id, payload)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    nutrition_service.delete_entry(db, user, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/daily/{logged_date}", response_model=NutritionDailySummary)
def daily_summary(
    logged_date: date,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.daily_summary(db, user, logged_date)


@router.post("/saved-meals", response_model=SavedMealResponse, status_code=status.HTTP_201_CREATED)
def create_saved_meal(
    payload: SavedMealCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.create_saved_meal(db, user, payload)


@router.get("/saved-meals", response_model=list[SavedMealResponse])
def list_saved_meals(
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.list_saved_meals(db, user)


@router.get("/saved-meals/{meal_id}", response_model=SavedMealResponse)
def get_saved_meal(
    meal_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.get_saved_meal(db, user, meal_id)


@router.patch("/saved-meals/{meal_id}", response_model=SavedMealResponse)
def update_saved_meal(
    meal_id: UUID,
    payload: SavedMealUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.update_saved_meal(db, user, meal_id, payload)


@router.delete("/saved-meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_meal(
    meal_id: UUID,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    nutrition_service.delete_saved_meal(db, user, meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/saved-meals/{meal_id}/log", response_model=list[NutritionEntryResponse], status_code=status.HTTP_201_CREATED)
def log_saved_meal(
    meal_id: UUID,
    payload: SavedMealLogRequest,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return nutrition_service.log_saved_meal(db, user, meal_id, payload)
