from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

CardioActivityType = Literal[
    "running",
    "walking",
    "cycling",
    "football",
    "basketball",
    "rowing",
    "swimming",
    "other",
]
HybridSessionType = Literal["hyrox_full", "hyrox_half", "hyrox_stations_only", "custom"]
HybridSegmentType = Literal["run", "station"]
WeightUnit = Literal["kg", "lb"]


class CardioActivityCreate(BaseModel):
    activity_type: CardioActivityType
    name: str = Field(min_length=1, max_length=160)
    activity_date: date
    duration_seconds: int = Field(gt=0, le=172800)
    distance_km: float | None = Field(default=None, ge=0, le=10000)
    notes: str | None = None
    client_updated_at: datetime | None = None


class CardioActivityUpdate(BaseModel):
    activity_type: CardioActivityType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    activity_date: date | None = None
    duration_seconds: int | None = Field(default=None, gt=0, le=172800)
    distance_km: float | None = Field(default=None, ge=0, le=10000)
    notes: str | None = None
    client_updated_at: datetime | None = None


class CardioActivityResponse(CardioActivityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    pace_seconds_per_km: float | None = None
    average_speed_kmh: float | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class HybridSegmentInput(BaseModel):
    position: int = Field(ge=0)
    segment_type: HybridSegmentType
    segment_name: str = Field(min_length=1, max_length=160)
    station_key: str | None = Field(default=None, max_length=80)
    target_distance_m: int | None = Field(default=None, ge=0, le=100000)
    target_reps: int | None = Field(default=None, ge=0, le=10000)
    load: float | None = Field(default=None, ge=0, le=5000)
    load_unit: WeightUnit | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0, le=172800)
    notes: str | None = None
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.started_at is not None and self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("segment completed_at cannot be earlier than started_at")
        return self


class HybridSessionCreate(BaseModel):
    session_type: HybridSessionType
    name: str = Field(min_length=1, max_length=160)
    started_at: datetime
    completed_at: datetime | None = None
    total_duration_seconds: int | None = Field(default=None, ge=0, le=172800)
    notes: str | None = None
    segments: list[HybridSegmentInput] = Field(default_factory=list)
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be earlier than started_at")
        return self


class HybridSessionUpdate(BaseModel):
    session_type: HybridSessionType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    completed_at: datetime | None = None
    total_duration_seconds: int | None = Field(default=None, ge=0, le=172800)
    notes: str | None = None
    client_updated_at: datetime | None = None


class HybridSegmentResponse(HybridSegmentInput):
    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class HybridSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    session_type: HybridSessionType
    name: str
    started_at: datetime
    completed_at: datetime | None
    total_duration_seconds: int | None
    notes: str | None
    segments: list[HybridSegmentResponse]
    client_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class HybridSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    session_type: HybridSessionType
    name: str
    started_at: datetime
    completed_at: datetime | None
    total_duration_seconds: int | None
    created_at: datetime
    updated_at: datetime
    version: int
