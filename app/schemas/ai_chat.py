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
