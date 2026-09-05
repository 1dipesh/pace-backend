from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExerciseType = Literal["weighted", "bodyweight", "duration"]
SetType = Literal["warmup", "working"]
WeightUnit = Literal["kg", "lb"]
EffortMode = Literal["off", "rir", "rpe"]


class TrainingExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    exercise_type: ExerciseType
    primary_muscle: str = Field(min_length=1, max_length=80)
    equipment: str | None = Field(default=None, max_length=80)
    is_favorite: bool = False
    client_updated_at: datetime | None = None


class TrainingExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    exercise_type: ExerciseType | None = None
    primary_muscle: str | None = Field(default=None, min_length=1, max_length=80)
    equipment: str | None = Field(default=None, max_length=80)
    is_favorite: bool | None = None
    client_updated_at: datetime | None = None


class TrainingExerciseResponse(TrainingExerciseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class TrainingSettingsUpsert(BaseModel):
    default_warmup_rest_seconds: int = Field(default=60, ge=0, le=3600)
    default_working_rest_seconds: int = Field(default=120, ge=0, le=3600)
    effort_mode: EffortMode = "rir"
    client_updated_at: datetime | None = None


class TrainingSettingsResponse(TrainingSettingsUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class TrainingTemplateSetInput(BaseModel):
    position: int = Field(ge=0)
    set_type: SetType
    target_reps: int | None = Field(default=None, ge=0, le=1000)
    target_weight: float | None = Field(default=None, ge=0)
    weight_unit: WeightUnit | None = None
    target_duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    client_updated_at: datetime | None = None


class TrainingTemplateExerciseInput(BaseModel):
    exercise_id: UUID
    position: int = Field(ge=0)
    notes: str | None = None
    sets: list[TrainingTemplateSetInput] = Field(default_factory=list)
    client_updated_at: datetime | None = None


class TrainingTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    notes: str | None = None
    source_program_id: str | None = Field(default=None, max_length=120)
    source_program_variant_id: str | None = Field(default=None, max_length=120)
    source_program_day_id: str | None = Field(default=None, max_length=120)
    source_program_name: str | None = Field(default=None, max_length=160)
    exercises: list[TrainingTemplateExerciseInput] = Field(default_factory=list)
    client_updated_at: datetime | None = None


class TrainingTemplateSetResponse(TrainingTemplateSetInput):
    id: UUID
    version: int


class TrainingTemplateExerciseResponse(BaseModel):
    id: UUID
    exercise_id: UUID
    position: int
    notes: str | None
    exercise_name: str
    exercise_type: ExerciseType
    primary_muscle: str
    sets: list[TrainingTemplateSetResponse]
    version: int


class TrainingTemplateResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    notes: str | None
    source_program_id: str | None
    source_program_variant_id: str | None
    source_program_day_id: str | None
    source_program_name: str | None
    exercises: list[TrainingTemplateExerciseResponse]
    client_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class TrainingTemplateSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    notes: str | None
    source_program_name: str | None
    created_at: datetime
    updated_at: datetime
    version: int


class TrainingSessionSetInput(BaseModel):
    position: int = Field(ge=0)
    set_type: SetType
    weight: float | None = Field(default=None, ge=0)
    weight_unit: WeightUnit | None = None
    reps: int | None = Field(default=None, ge=0, le=1000)
    duration_seconds: int | None = Field(default=None, ge=0, le=86400)
    effort_mode: EffortMode = "off"
    rir: float | None = Field(default=None, ge=0, le=10)
    rpe: float | None = Field(default=None, ge=1, le=10)
    rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    completed_at: datetime | None = None
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_effort(self):
        if self.effort_mode == "rir" and self.rir is None:
            raise ValueError("rir is required when effort_mode is 'rir'")
        if self.effort_mode == "rpe" and self.rpe is None:
            raise ValueError("rpe is required when effort_mode is 'rpe'")
        return self


class TrainingSessionExerciseInput(BaseModel):
    exercise_id: UUID
    position: int = Field(ge=0)
    notes: str | None = None
    rest_override_seconds: int | None = Field(default=None, ge=0, le=3600)
    sets: list[TrainingSessionSetInput] = Field(default_factory=list)
    client_updated_at: datetime | None = None


class TrainingSessionCreate(BaseModel):
    template_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    notes: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    exercises: list[TrainingSessionExerciseInput] = Field(default_factory=list)
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_times(self):
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at cannot be earlier than started_at")
        return self


class TrainingSessionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    notes: str | None = None
    completed_at: datetime | None = None
    client_updated_at: datetime | None = None


class TrainingSetResponse(TrainingSessionSetInput):
    id: UUID
    version: int


class TrainingSessionExerciseResponse(BaseModel):
    id: UUID
    exercise_id: UUID | None
    position: int
    exercise_name_snapshot: str
    exercise_type_snapshot: ExerciseType
    primary_muscle_snapshot: str
    notes: str | None
    rest_override_seconds: int | None
    sets: list[TrainingSetResponse]
    version: int


class TrainingSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    template_id: UUID | None
    name: str
    notes: str | None
    started_at: datetime
    completed_at: datetime | None
    exercises: list[TrainingSessionExerciseResponse]
    client_updated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    version: int


class TrainingSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    template_id: UUID | None
    name: str
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    version: int
