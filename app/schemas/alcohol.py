from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AlcoholCategory = Literal["beer", "wine", "spirits", "cocktail", "other"]
AlcoholEntryMode = Literal["live", "historical"]
AlcoholSessionStatus = Literal["active", "completed"]
AlcoholBreakStatus = Literal["running", "completed", "interrupted", "cancelled"]


class AlcoholSessionCreate(BaseModel):
    entry_mode: AlcoholEntryMode
    historical_date: date | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    notes: str | None = None
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_mode(self):
        if self.entry_mode == "live":
            if self.started_at is None:
                raise ValueError("started_at is required for a live session")
            if self.historical_date is not None:
                raise ValueError("historical_date is only used for historical sessions")
            if self.ended_at is not None and self.ended_at < self.started_at:
                raise ValueError("ended_at cannot be earlier than started_at")
        else:
            if self.historical_date is None:
                raise ValueError("historical_date is required for a historical session")
            if self.started_at is not None or self.ended_at is not None:
                raise ValueError("historical sessions do not use live timing fields")
        return self


class AlcoholSessionUpdate(BaseModel):
    notes: str | None = None
    client_updated_at: datetime | None = None


class AlcoholSessionAction(BaseModel):
    at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholDrinkCreate(BaseModel):
    category: AlcoholCategory
    name: str = Field(min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    volume_ml: float = Field(gt=0, le=10000)
    abv_percent: float = Field(ge=0, le=100)
    logged_at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholDrinkUpdate(BaseModel):
    category: AlcoholCategory | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    volume_ml: float | None = Field(default=None, gt=0, le=10000)
    abv_percent: float | None = Field(default=None, ge=0, le=100)
    logged_at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholDrinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    session_id: UUID
    category: AlcoholCategory
    name: str
    brand: str | None
    volume_ml: float
    abv_percent: float
    alcohol_grams: float
    pace_units: float
    logged_at: datetime | None
    client_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class AlcoholWaterCreate(BaseModel):
    volume_ml: int | None = Field(default=None, gt=0, le=20000)
    container: str | None = Field(default=None, max_length=80)
    logged_at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholWaterUpdate(BaseModel):
    volume_ml: int | None = Field(default=None, gt=0, le=20000)
    container: str | None = Field(default=None, max_length=80)
    logged_at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholWaterResponse(AlcoholWaterCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    session_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class AlcoholBreakCreate(BaseModel):
    planned_duration_seconds: int = Field(gt=0, le=86400)
    started_at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholBreakUpdate(BaseModel):
    status: Literal["completed", "cancelled"] | None = None
    ended_at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholBreakResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    session_id: UUID
    planned_duration_seconds: int
    status: AlcoholBreakStatus
    started_at: datetime
    ended_at: datetime | None
    interrupted_by_drink_id: UUID | None
    client_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class AlcoholFavoriteCreate(BaseModel):
    category: AlcoholCategory
    name: str = Field(min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    volume_ml: float = Field(gt=0, le=10000)
    abv_percent: float = Field(ge=0, le=100)
    client_updated_at: datetime | None = None


class AlcoholFavoriteUpdate(BaseModel):
    category: AlcoholCategory | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    brand: str | None = Field(default=None, max_length=160)
    volume_ml: float | None = Field(default=None, gt=0, le=10000)
    abv_percent: float | None = Field(default=None, ge=0, le=100)
    client_updated_at: datetime | None = None


class AlcoholFavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    category: AlcoholCategory
    name: str
    brand: str | None
    volume_ml: float
    abv_percent: float
    usage_count: int
    last_used_at: datetime | None
    client_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class AlcoholFavoriteLog(BaseModel):
    session_id: UUID
    logged_at: datetime | None = None
    client_updated_at: datetime | None = None


class AlcoholSessionSummary(BaseModel):
    id: UUID
    user_id: UUID
    entry_mode: AlcoholEntryMode
    status: AlcoholSessionStatus
    session_date: date
    started_at: datetime | None
    ended_at: datetime | None
    paused_at: datetime | None
    total_paused_seconds: int
    notes: str | None
    drink_count: int
    total_alcohol_grams: float
    total_pace_units: float
    total_water_ml: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class AlcoholSessionResponse(AlcoholSessionSummary):
    drinks: list[AlcoholDrinkResponse]
    water_entries: list[AlcoholWaterResponse]
    breaks: list[AlcoholBreakResponse]
    client_updated_at: datetime | None
