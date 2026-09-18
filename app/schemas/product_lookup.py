from typing import Literal

from pydantic import BaseModel, Field


class BarcodeNutrition(BaseModel):
    calories: float = Field(ge=0)
    protein: float = Field(ge=0)
    carbs: float = Field(ge=0)
    fat: float = Field(ge=0)
    fiber: float | None = Field(default=None, ge=0)


class BarcodeProductResponse(BaseModel):
    barcode: str
    name: str
    brand: str | None = None
    basis_amount: float = Field(gt=0)
    basis_unit: Literal["g", "ml", "piece", "serving"]
    serving_label: str | None = None
    nutrition: BarcodeNutrition
    source: Literal["open_food_facts"] = "open_food_facts"
    source_url: str
