from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AiPlanResponse(BaseModel):
    plan: Literal["beta", "free", "pro"]
    monthly_limit: int | None
    used_this_month: int
    remaining: int | None
    unlimited: bool


class AiMessageCreate(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(min_length=1, max_length=2000)


class AiMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime


class AiConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AiConversationResponse(AiConversationSummary):
    messages: list[AiMessageResponse]


class AiChatResponse(BaseModel):
    conversation: AiConversationSummary
    message: AiMessageResponse
    plan: AiPlanResponse
    safety_intervened: bool = False


class FoodPhotoRequest(BaseModel):
    image_data_url: str = Field(min_length=32)


class FoodPhotoItem(BaseModel):
    name: str
    portion_description: str
    calories: float = Field(ge=0, le=5000)
    protein: float = Field(ge=0, le=1000)
    carbs: float = Field(ge=0, le=1000)
    fat: float = Field(ge=0, le=1000)
    fiber: float | None = Field(default=None, ge=0, le=500)
    confidence: Literal["low", "medium", "high"]


class FoodPhotoResponse(BaseModel):
    items: list[FoodPhotoItem]
    notes: str
    plan: AiPlanResponse
