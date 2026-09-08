import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    display_name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime
