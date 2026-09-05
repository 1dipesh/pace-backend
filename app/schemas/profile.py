from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

CalorieEstimateSex = Literal["male", "female", "neutral"]
PaceGoal = Literal[
    "lose_body_fat",
    "maintain",
    "build_muscle",
    "improve_performance",
    "general_health",
]
ActivityLevel = Literal["mostly_sedentary", "lightly_active", "active", "very_active"]
TrainingExperience = Literal["beginner", "intermediate", "experienced"]


def calculate_age(date_of_birth: date, today: date | None = None) -> int:
    today = today or date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age


class PaceProfileFields(BaseModel):
    date_of_birth: date
    height_cm: float = Field(gt=0, le=300)
    weight_kg: float = Field(gt=0, le=1000)
    calorie_estimate_sex: CalorieEstimateSex
    goal: PaceGoal
    activity_level: ActivityLevel
    training_experience: TrainingExperience
    training_days_per_week: int = Field(ge=0, le=6)

    @model_validator(mode="after")
    def validate_age(self):
        age = calculate_age(self.date_of_birth)
        if age < 18 or age > 90:
            raise ValueError("date_of_birth must produce an age between 18 and 90")
        return self


class PaceProfileCreate(PaceProfileFields):
    client_updated_at: datetime | None = None


class PaceProfileUpdate(BaseModel):
    date_of_birth: date | None = None
    height_cm: float | None = Field(default=None, gt=0, le=300)
    weight_kg: float | None = Field(default=None, gt=0, le=1000)
    calorie_estimate_sex: CalorieEstimateSex | None = None
    goal: PaceGoal | None = None
    activity_level: ActivityLevel | None = None
    training_experience: TrainingExperience | None = None
    training_days_per_week: int | None = Field(default=None, ge=0, le=6)
    client_updated_at: datetime | None = None

    @model_validator(mode="after")
    def reject_null_profile_fields(self):
        required_profile_fields = {
            "date_of_birth",
            "height_cm",
            "weight_kg",
            "calorie_estimate_sex",
            "goal",
            "activity_level",
            "training_experience",
            "training_days_per_week",
        }
        for field_name in self.model_fields_set & required_profile_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class PaceProfileResponse(PaceProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    age: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None
    client_updated_at: datetime | None
    version: int
