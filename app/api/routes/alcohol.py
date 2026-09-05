from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import PaceUser
from app.schemas.alcohol import (
    AlcoholBreakCreate,
    AlcoholBreakResponse,
    AlcoholBreakUpdate,
    AlcoholDrinkCreate,
    AlcoholDrinkResponse,
    AlcoholDrinkUpdate,
    AlcoholFavoriteCreate,
    AlcoholFavoriteLog,
    AlcoholFavoriteResponse,
    AlcoholFavoriteUpdate,
    AlcoholSessionAction,
    AlcoholSessionCreate,
    AlcoholSessionResponse,
    AlcoholSessionSummary,
    AlcoholSessionUpdate,
    AlcoholWaterCreate,
    AlcoholWaterResponse,
    AlcoholWaterUpdate,
)
from app.services import alcohol_service

router = APIRouter(prefix="/api/v1/alcohol", tags=["alcohol"])


@router.post("/sessions", response_model=AlcoholSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: AlcoholSessionCreate, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    return alcohol_service.create_session(db, user, payload)


@router.get("/sessions", response_model=list[AlcoholSessionSummary])
def list_sessions(
    from_date: date | None = None,
    to_date: date | None = None,
    entry_mode: str | None = Query(default=None, pattern="^(live|historical)$"),
    session_status: str | None = Query(default=None, alias="status", pattern="^(active|completed)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.list_sessions(
        db,
        user,
        from_date=from_date,
        to_date=to_date,
        entry_mode=entry_mode,
        session_status=session_status,
        limit=limit,
    )


@router.get("/sessions/active", response_model=AlcoholSessionResponse)
def get_active_session(db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    return alcohol_service.get_active_session(db, user)


@router.get("/sessions/{session_id}", response_model=AlcoholSessionResponse)
def get_session(session_id: UUID, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    return alcohol_service.get_session(db, user, session_id)


@router.patch("/sessions/{session_id}", response_model=AlcoholSessionResponse)
def update_session(
    session_id: UUID,
    payload: AlcoholSessionUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.update_session(db, user, session_id, payload)


@router.post("/sessions/{session_id}/pause", response_model=AlcoholSessionResponse)
def pause_session(
    session_id: UUID,
    payload: AlcoholSessionAction,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.pause_session(db, user, session_id, payload)


@router.post("/sessions/{session_id}/resume", response_model=AlcoholSessionResponse)
def resume_session(
    session_id: UUID,
    payload: AlcoholSessionAction,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.resume_session(db, user, session_id, payload)


@router.post("/sessions/{session_id}/complete", response_model=AlcoholSessionResponse)
def complete_session(
    session_id: UUID,
    payload: AlcoholSessionAction,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.complete_session(db, user, session_id, payload)


@router.post("/sessions/{session_id}/reopen", response_model=AlcoholSessionResponse)
def reopen_session(
    session_id: UUID,
    payload: AlcoholSessionAction,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.reopen_session(db, user, session_id, payload)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: UUID, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    alcohol_service.delete_session(db, user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/drinks", response_model=AlcoholDrinkResponse, status_code=status.HTTP_201_CREATED)
def add_drink(
    session_id: UUID,
    payload: AlcoholDrinkCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.add_drink(db, user, session_id, payload)


@router.patch("/drinks/{drink_id}", response_model=AlcoholDrinkResponse)
def update_drink(
    drink_id: UUID,
    payload: AlcoholDrinkUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.update_drink(db, user, drink_id, payload)


@router.delete("/drinks/{drink_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_drink(drink_id: UUID, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    alcohol_service.delete_drink(db, user, drink_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/water", response_model=AlcoholWaterResponse, status_code=status.HTTP_201_CREATED)
def add_water(
    session_id: UUID,
    payload: AlcoholWaterCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.add_water(db, user, session_id, payload)


@router.patch("/water/{entry_id}", response_model=AlcoholWaterResponse)
def update_water(
    entry_id: UUID,
    payload: AlcoholWaterUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.update_water(db, user, entry_id, payload)


@router.delete("/water/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_water(entry_id: UUID, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    alcohol_service.delete_water(db, user, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/sessions/{session_id}/breaks", response_model=AlcoholBreakResponse, status_code=status.HTTP_201_CREATED)
def add_break(
    session_id: UUID,
    payload: AlcoholBreakCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.add_break(db, user, session_id, payload)


@router.patch("/breaks/{break_id}", response_model=AlcoholBreakResponse)
def update_break(
    break_id: UUID,
    payload: AlcoholBreakUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.update_break(db, user, break_id, payload)


@router.delete("/breaks/{break_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_break(break_id: UUID, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    alcohol_service.delete_break(db, user, break_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/favorites", response_model=AlcoholFavoriteResponse, status_code=status.HTTP_201_CREATED)
def create_favorite(
    payload: AlcoholFavoriteCreate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.create_favorite(db, user, payload)


@router.get("/favorites", response_model=list[AlcoholFavoriteResponse])
def list_favorites(db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    return alcohol_service.list_favorites(db, user)


@router.get("/favorites/{favorite_id}", response_model=AlcoholFavoriteResponse)
def get_favorite(favorite_id: UUID, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    return alcohol_service.get_favorite(db, user, favorite_id)


@router.patch("/favorites/{favorite_id}", response_model=AlcoholFavoriteResponse)
def update_favorite(
    favorite_id: UUID,
    payload: AlcoholFavoriteUpdate,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.update_favorite(db, user, favorite_id, payload)


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite(favorite_id: UUID, db: Session = Depends(get_db), user: PaceUser = Depends(get_current_user)):
    alcohol_service.delete_favorite(db, user, favorite_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/favorites/{favorite_id}/log", response_model=AlcoholDrinkResponse, status_code=status.HTTP_201_CREATED)
def log_favorite(
    favorite_id: UUID,
    payload: AlcoholFavoriteLog,
    db: Session = Depends(get_db),
    user: PaceUser = Depends(get_current_user),
):
    return alcohol_service.log_favorite(db, user, favorite_id, payload)
