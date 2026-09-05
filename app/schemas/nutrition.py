from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

NutritionUnit = Literal["g", "ml", "piece", "serving"]
MealType = Literal["breakfast", "lunch", "dinner", "snack", "other"]
PreparationState = Literal["unspecified", "raw", "cooked"]
FoodSource = Literal["starter", "custom", "label"]


class SyncResponseFields(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    client_updated_at: datetime | None
    version: int


class NutritionGoalsUpsert(BaseModel):
    target_calories_kcal: float = Field(gt=0, le=20000)
    target_protein_g: float = Field(ge=0, le=2000)
    target_carbs_g: float = Field(ge=0, le=3000)
    target_fat_g: float = Field(ge=0, le=1000)
    target_fiber_g: float | None = Field(default=None, ge=0, le=500)
    client_updated_at: datetime | None = None


class NutritionGoalsResponse(NutritionGoalsUpsert, SyncResponseFields):
    pass


class NutritionFoodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    basis_amount: float = Field(gt=0, le=100000)
    basis_unit: NutritionUnit
    calories_kcal: float = Field(ge=0, le=100000)
    protein_g: float = Field(ge=0, le=10000)
    carbs_g: float = Field(ge=0, le=10000)
    fat_g: float = Field(ge=0, le=10000)
    fiber_g: float | None = Field(default=None, ge=0, le=10000)
    preparation_state: PreparationState = "unspecified"
    source: FoodSource = "custom"
    is_favorite: bool = False
    client_updated_at: datetime | None = None


class NutritionFoodUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    basis_amount: float | None = Field(default=None, gt=0, le=100000)
    basis_unit: NutritionUnit | None = None
    calories_kcal: float | None = Field(default=None, ge=0, le=100000)
    protein_g: float | None = Field(default=None, ge=0, le=10000)
    carbs_g: float | None = Field(default=None, ge=0, le=10000)
    fat_g: float | None = Field(default=None, ge=0, le=10000)
    fiber_g: float | None = Field(default=None, ge=0, le=10000)
    preparation_state: PreparationState | None = None
    source: FoodSource | None = None
    is_favorite: bool | None = None
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        required = {
            "name",
            "basis_amount",
            "basis_unit",
            "calories_kcal",
            "protein_g",
            "carbs_g",
            "fat_g",
            "preparation_state",
            "source",
            "is_favorite",
        }
        for field_name in self.model_fields_set & required:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class NutritionFoodResponse(NutritionFoodCreate, SyncResponseFields):
    pass


class ManualNutritionEntry(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    amount: float = Field(gt=0, le=100000)
    unit: NutritionUnit
    calories_kcal: float = Field(ge=0, le=100000)
    protein_g: float = Field(ge=0, le=10000)
    carbs_g: float = Field(ge=0, le=10000)
    fat_g: float = Field(ge=0, le=10000)
    fiber_g: float | None = Field(default=None, ge=0, le=10000)
    preparation_state: PreparationState = "unspecified"


class NutritionEntryCreate(BaseModel):
    logged_date: date
    meal_type: MealType
    food_id: UUID | None = None
    amount: float | None = Field(default=None, gt=0, le=100000)
    unit: NutritionUnit | None = None
    manual: ManualNutritionEntry | None = None
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_source(self):
        using_food = self.food_id is not None
        using_manual = self.manual is not None
        if using_food == using_manual:
            raise ValueError("provide exactly one of food_id or manual")
        if using_food and (self.amount is None or self.unit is None):
            raise ValueError("amount and unit are required when food_id is provided")
        if using_manual and (self.amount is not None or self.unit is not None):
            raise ValueError("amount and unit belong inside manual when logging a manual food")
        return self


class NutritionEntryUpdate(BaseModel):
    logged_date: date | None = None
    meal_type: MealType | None = None
    amount: float | None = Field(default=None, gt=0, le=100000)
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def reject_null_fields(self):
        required = {"logged_date", "meal_type", "amount"}
        for field_name in self.model_fields_set & required:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class NutritionEntryResponse(SyncResponseFields):
    logged_date: date
    meal_type: MealType
    amount: float
    unit: NutritionUnit
    source_food_id: UUID | None
    food_name: str
    brand: str | None
    preparation_state: PreparationState
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None


class NutritionTotals(BaseModel):
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None


class NutritionDailySummary(BaseModel):
    logged_date: date
    totals: NutritionTotals
    goals: NutritionGoalsResponse | None
    entries: list[NutritionEntryResponse]


class SavedMealItemWrite(BaseModel):
    food_id: UUID
    amount: float = Field(gt=0, le=100000)
    unit: NutritionUnit


class SavedMealCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    items: list[SavedMealItemWrite] = Field(min_length=1, max_length=100)
    client_updated_at: datetime | None = None


class SavedMealUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    items: list[SavedMealItemWrite] | None = Field(default=None, min_length=1, max_length=100)
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def reject_null_fields(self):
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        if "items" in self.model_fields_set and self.items is None:
            raise ValueError("items cannot be null")
        return self


class SavedMealItemResponse(SyncResponseFields):
    meal_id: UUID
    food_id: UUID
    amount: float
    unit: NutritionUnit
    position: int
    food_name: str
    brand: str | None
    food_deleted: bool
    calories_kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None


class SavedMealResponse(SyncResponseFields):
    name: str
    items: list[SavedMealItemResponse]
    totals: NutritionTotals


class SavedMealLogRequest(BaseModel):
    logged_date: date
    meal_type: MealType
    client_updated_at: datetime | None = None
