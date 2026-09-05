from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.schemas.profile import PaceProfileCreate, PaceProfileResponse, PaceProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.post("", response_model=PaceProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: PaceProfileCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
) -> PaceProfileResponse:
    return profile_service.create_profile(db, user, payload)


@router.get("", response_model=PaceProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
) -> PaceProfileResponse:
    return profile_service.get_profile(db, user)


@router.patch("", response_model=PaceProfileResponse)
def update_profile(
    payload: PaceProfileUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
) -> PaceProfileResponse:
    return profile_service.update_profile(db, user, payload)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
) -> Response:
    profile_service.delete_profile(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
