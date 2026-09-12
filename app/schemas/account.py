from typing import Literal

from pydantic import BaseModel


class DeletePaceAccountRequest(BaseModel):
    confirmation: Literal["DELETE"]


class DeletePaceAccountResponse(BaseModel):
    deleted: bool
