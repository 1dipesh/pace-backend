from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import PaceUser
from app.schemas.auth import CurrentUserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUserResponse)
def get_authenticated_user(
    user: PaceUser = Depends(get_current_user),
) -> CurrentUserResponse:
    """Return the Pace account linked to the validated Supabase access token."""
    return user
