from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

Id = Annotated[str, Field(min_length=1, max_length=180, pattern=r"^[A-Za-z0-9_-]+$")]
Text = Annotated[str, Field(min_length=1, max_length=160)]
Number = Annotated[float, Field(ge=0, le=999999, allow_inf_nan=False)]
Positive = Annotated[float, Field(ge=0.01, le=100000, allow_inf_nan=False)]
Unit = Literal["g", "ml", "piece", "serving"]
Entity = Literal["foods", "meals", "entries", "goals"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: Id
    updatedAt: datetime


class Values(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calories: Number = Field(le=100000)
    protein: Number = Field(le=10000)
    carbs: Number = Field(le=10000)
    fat: Number = Field(le=10000)
    fiber: Number | None = Field(default=None, le=10000)


class Food(Record):
    name: Text
    brand: Text | None = None
    preparation: Text | None = None
    category: Literal["protein", "carb", "fruit", "vegetable", "dairy", "fat", "other"]
    basisAmount: Positive
    basisUnit: Unit
    servingLabel: Text | None = None
    nutrition: Values
    isStarter: bool
    isLibraryItem: bool | None = None
    isFavorite: bool | None = None
    usageCount: int | None = Field(default=None, ge=0)
    lastUsedAt: datetime | None = None
    lastUsedAmount: Positive | None = None
    note: str | None = Field(default=None, max_length=4000)
    createdAt: datetime


class Item(BaseModel):
    model_config = ConfigDict(extra="forbid")
    foodId: Id
    amount: Positive


class Meal(Record):
    name: Text
    items: list[Item] = Field(min_length=1, max_length=200)
    usageCount: int | None = Field(default=None, ge=0)
    lastUsedAt: datetime | None = None
    createdAt: datetime


class Entry(Record):
    foodId: Id
    date: date
    amount: Positive
    unit: Unit
    servingLabel: Text | None = None
    foodName: Text
    foodBrand: Text | None = None
    foodPreparation: Text | None = None
    nutrition: Values
    mealGroupId: Id | None = None
    mealTemplateId: Id | None = None
    mealName: Text | None = None
    loggedAt: datetime
    createdAt: datetime


class Goals(Record):
    id: Literal["default"]
    calories: Positive | None = Field(default=None, le=20000)
    protein: Number | None = Field(default=None, le=2000)
    carbs: Number | None = Field(default=None, le=3000)
    fat: Number | None = Field(default=None, le=1000)
    fiber: Number | None = Field(default=None, le=500)


SCHEMAS = {"foods": Food, "meals": Meal, "entries": Entry, "goals": Goals}


class Change(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity: Entity
    id: Id
    expected_version: int = Field(ge=0)
    data: dict | None

    @model_validator(mode="after")
    def validate_data(self):
        if self.entity == "goals" and self.id != "default":
            raise ValueError("Goals id must be default")
        if self.data is not None:
            value = SCHEMAS[self.entity].model_validate(self.data)
            if value.id != self.id:
                raise ValueError("Record id does not match change id")
            # Validate without rewriting timestamps or adding optional fields:
            # the wire record is also the client's exact three-way merge base.
        return self


class Mutation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mutation_id: UUID
    changes: list[Change] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def unique_keys(self):
        if len({(c.entity, c.id) for c in self.changes}) != len(self.changes):
            raise ValueError("Duplicate change key")
        return self
