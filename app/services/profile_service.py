from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.profile import PaceProfile
from app.models.user import PaceUser
from app.repositories import profile_repository
from app.schemas.profile import (
    PaceProfileCreate,
    PaceProfileResponse,
    PaceProfileUpdate,
    calculate_age,
)


def to_response(profile: PaceProfile) -> PaceProfileResponse:
    return PaceProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        date_of_birth=profile.date_of_birth,
        age=calculate_age(profile.date_of_birth),
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        calorie_estimate_sex=profile.calorie_estimate_sex,
        goal=profile.goal,
        activity_level=profile.activity_level,
        training_experience=profile.training_experience,
        training_days_per_week=profile.training_days_per_week,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        deleted_at=profile.deleted_at,
        client_updated_at=profile.client_updated_at,
        version=profile.version,
    )


def create_profile(db: Session, user: PaceUser, payload: PaceProfileCreate) -> PaceProfileResponse:
    try:
        profile = profile_repository.create_profile(db, user.id, payload)
    except ValueError as exc:
        if str(exc) == "profile_exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Profile already exists",
            ) from exc
        raise
    return to_response(profile)


def get_profile(db: Session, user: PaceUser) -> PaceProfileResponse:
    profile = profile_repository.get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return to_response(profile)


def update_profile(
    db: Session,
    user: PaceUser,
    payload: PaceProfileUpdate,
) -> PaceProfileResponse:
    profile = profile_repository.get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return to_response(profile)

    # Validate the resulting DOB, including partial updates.
    if payload.date_of_birth is not None:
        age = calculate_age(payload.date_of_birth)
        if age < 18 or age > 90:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="date_of_birth must produce an age between 18 and 90",
            )

    profile = profile_repository.update_profile(db, profile, payload)
    return to_response(profile)


def delete_profile(db: Session, user: PaceUser) -> None:
    profile = profile_repository.get_profile(db, user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    profile_repository.soft_delete_profile(db, profile)
