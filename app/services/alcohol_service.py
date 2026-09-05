from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import PaceUser
from app.repositories import alcohol_repository as repo
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


def _not_found(label: str):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aligned(a: datetime, b: datetime) -> tuple[datetime, datetime]:
    if a.tzinfo is None and b.tzinfo is not None:
        a = a.replace(tzinfo=b.tzinfo)
    elif b.tzinfo is None and a.tzinfo is not None:
        b = b.replace(tzinfo=a.tzinfo)
    return a, b


def _is_before(a: datetime, b: datetime) -> bool:
    a, b = _aligned(a, b)
    return a < b


def _elapsed_seconds(start: datetime, end: datetime) -> int:
    start, end = _aligned(start, end)
    return int((end - start).total_seconds())


def _ensure_same_session(row, session_id: UUID, label: str):
    if row.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} not found in this session",
        )


def _drink_response(row) -> AlcoholDrinkResponse:
    grams = float(row.alcohol_grams)
    return AlcoholDrinkResponse(
        id=row.id,
        user_id=row.user_id,
        session_id=row.session_id,
        category=row.category,
        name=row.name,
        brand=row.brand,
        volume_ml=float(row.volume_ml),
        abv_percent=float(row.abv_percent),
        alcohol_grams=grams,
        pace_units=round(grams / 10, 3),
        logged_at=row.logged_at,
        client_updated_at=row.client_updated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        version=row.version,
    )


def _water_response(row) -> AlcoholWaterResponse:
    return AlcoholWaterResponse.model_validate(row)


def _break_response(row) -> AlcoholBreakResponse:
    return AlcoholBreakResponse.model_validate(row)


def _favorite_response(row) -> AlcoholFavoriteResponse:
    return AlcoholFavoriteResponse(
        id=row.id,
        user_id=row.user_id,
        category=row.category,
        name=row.name,
        brand=row.brand,
        volume_ml=float(row.volume_ml),
        abv_percent=float(row.abv_percent),
        usage_count=row.usage_count,
        last_used_at=row.last_used_at,
        client_updated_at=row.client_updated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        version=row.version,
    )


def _session_response(db: Session, user: PaceUser, row) -> AlcoholSessionResponse:
    drinks = [_drink_response(item) for item in repo.list_drinks(db, user.id, row.id)]
    water = [_water_response(item) for item in repo.list_water_entries(db, user.id, row.id)]
    breaks = [_break_response(item) for item in repo.list_breaks(db, user.id, row.id)]
    total_grams = round(sum(item.alcohol_grams for item in drinks), 3)
    total_water = sum(item.volume_ml or 0 for item in water)
    return AlcoholSessionResponse(
        id=row.id,
        user_id=row.user_id,
        entry_mode=row.entry_mode,
        status=row.status,
        session_date=row.session_date,
        started_at=row.started_at,
        ended_at=row.ended_at,
        paused_at=row.paused_at,
        total_paused_seconds=row.total_paused_seconds,
        notes=row.notes,
        drink_count=len(drinks),
        total_alcohol_grams=total_grams,
        total_pace_units=round(total_grams / 10, 3),
        total_water_ml=total_water,
        drinks=drinks,
        water_entries=water,
        breaks=breaks,
        client_updated_at=row.client_updated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        version=row.version,
    )


def _session_summary(db: Session, user: PaceUser, row) -> AlcoholSessionSummary:
    drinks = repo.list_drinks(db, user.id, row.id)
    water = repo.list_water_entries(db, user.id, row.id)
    total_grams = round(sum(float(item.alcohol_grams) for item in drinks), 3)
    return AlcoholSessionSummary(
        id=row.id,
        user_id=row.user_id,
        entry_mode=row.entry_mode,
        status=row.status,
        session_date=row.session_date,
        started_at=row.started_at,
        ended_at=row.ended_at,
        paused_at=row.paused_at,
        total_paused_seconds=row.total_paused_seconds,
        notes=row.notes,
        drink_count=len(drinks),
        total_alcohol_grams=total_grams,
        total_pace_units=round(total_grams / 10, 3),
        total_water_ml=sum(item.volume_ml or 0 for item in water),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
        version=row.version,
    )


def create_session(db: Session, user: PaceUser, payload: AlcoholSessionCreate):
    if payload.entry_mode == "live":
        if repo.get_active_live_session(db, user.id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active live alcohol session already exists",
            )
        session_date = payload.started_at.date()
    else:
        session_date = payload.historical_date

    row = repo.create_session(
        db,
        user.id,
        entry_mode=payload.entry_mode,
        session_date=session_date,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        notes=payload.notes,
        client_updated_at=payload.client_updated_at,
    )
    return _session_response(db, user, row)


def list_sessions(
    db: Session,
    user: PaceUser,
    *,
    from_date: date | None,
    to_date: date | None,
    entry_mode: str | None,
    session_status: str | None,
    limit: int,
):
    if from_date is not None and to_date is not None and to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="to_date cannot be earlier than from_date",
        )
    return [
        _session_summary(db, user, row)
        for row in repo.list_sessions(
            db,
            user.id,
            from_date=from_date,
            to_date=to_date,
            entry_mode=entry_mode,
            session_status=session_status,
            limit=limit,
        )
    ]


def get_active_session(db: Session, user: PaceUser):
    row = repo.get_active_live_session(db, user.id)
    if row is None:
        _not_found("Active alcohol session")
    return _session_response(db, user, row)


def get_session(db: Session, user: PaceUser, session_id: UUID):
    row = repo.get_session(db, user.id, session_id)
    if row is None:
        _not_found("Alcohol session")
    return _session_response(db, user, row)


def update_session(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholSessionUpdate):
    row = repo.get_session(db, user.id, session_id)
    if row is None:
        _not_found("Alcohol session")
    if not payload.model_dump(exclude_unset=True):
        return _session_response(db, user, row)
    return _session_response(db, user, repo.update_session(db, row, payload))


def pause_session(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholSessionAction):
    row = repo.get_session(db, user.id, session_id)
    if row is None:
        _not_found("Alcohol session")
    if row.entry_mode != "live" or row.status != "active":
        raise HTTPException(status_code=409, detail="Only an active live session can be paused")
    if row.paused_at is not None:
        raise HTTPException(status_code=409, detail="Session is already paused")
    at = payload.at or _now()
    if _is_before(at, row.started_at):
        raise HTTPException(status_code=422, detail="Pause time cannot be earlier than session start")
    row.paused_at = at
    row.client_updated_at = payload.client_updated_at
    return _session_response(db, user, repo.save_session(db, row))


def _resume_row(row, at: datetime):
    if row.paused_at is None:
        return
    if _is_before(at, row.paused_at):
        raise HTTPException(status_code=422, detail="Resume time cannot be earlier than pause time")
    row.total_paused_seconds += _elapsed_seconds(row.paused_at, at)
    row.paused_at = None


def resume_session(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholSessionAction):
    row = repo.get_session(db, user.id, session_id)
    if row is None:
        _not_found("Alcohol session")
    if row.entry_mode != "live" or row.status != "active":
        raise HTTPException(status_code=409, detail="Only an active live session can be resumed")
    if row.paused_at is None:
        raise HTTPException(status_code=409, detail="Session is not paused")
    _resume_row(row, payload.at or _now())
    row.client_updated_at = payload.client_updated_at
    return _session_response(db, user, repo.save_session(db, row))


def complete_session(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholSessionAction):
    row = repo.get_session(db, user.id, session_id)
    if row is None:
        _not_found("Alcohol session")
    if row.entry_mode != "live" or row.status != "active":
        raise HTTPException(status_code=409, detail="Only an active live session can be completed")
    at = payload.at or _now()
    if _is_before(at, row.started_at):
        raise HTTPException(status_code=422, detail="End time cannot be earlier than session start")
    if row.paused_at is not None:
        _resume_row(row, at)
    row.status = "completed"
    row.ended_at = at
    row.client_updated_at = payload.client_updated_at
    return _session_response(db, user, repo.save_session(db, row))


def reopen_session(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholSessionAction):
    row = repo.get_session(db, user.id, session_id)
    if row is None:
        _not_found("Alcohol session")
    if row.entry_mode != "live" or row.status != "completed" or row.ended_at is None:
        raise HTTPException(status_code=409, detail="Only a completed live session can be reopened")
    active = repo.get_active_live_session(db, user.id)
    if active is not None and active.id != row.id:
        raise HTTPException(status_code=409, detail="Another active live alcohol session already exists")
    at = payload.at or _now()
    if _is_before(at, row.ended_at):
        raise HTTPException(status_code=422, detail="Reopen time cannot be earlier than the prior end time")
    row.total_paused_seconds += _elapsed_seconds(row.ended_at, at)
    row.status = "active"
    row.ended_at = None
    row.paused_at = None
    row.client_updated_at = payload.client_updated_at
    return _session_response(db, user, repo.save_session(db, row))


def delete_session(db: Session, user: PaceUser, session_id: UUID):
    row = repo.get_session(db, user.id, session_id)
    if row is None:
        _not_found("Alcohol session")
    repo.soft_delete_session_graph(db, user.id, row)


def _prepare_live_event(row, at: datetime):
    if row.entry_mode != "live":
        return
    if row.status != "active":
        raise HTTPException(status_code=409, detail="Drinks can only be added to an active live session or historical session")
    if _is_before(at, row.started_at):
        raise HTTPException(status_code=422, detail="Event time cannot be earlier than session start")
    if row.paused_at is not None:
        _resume_row(row, at)


def add_drink(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholDrinkCreate):
    session = repo.get_session(db, user.id, session_id)
    if session is None:
        _not_found("Alcohol session")

    event_time = payload.logged_at or (_now() if session.entry_mode == "live" else None)
    if session.entry_mode == "historical" and payload.logged_at is not None:
        event_time = payload.logged_at
    if session.entry_mode == "live":
        _prepare_live_event(session, event_time)
        session.client_updated_at = payload.client_updated_at

    normalized = payload.model_copy(update={"logged_at": event_time})
    drink = repo.create_drink(db, user.id, session.id, normalized)

    if session.entry_mode == "live":
        for break_row in repo.get_running_breaks(db, user.id, session.id):
            break_row.status = "interrupted"
            break_row.ended_at = event_time
            break_row.interrupted_by_drink_id = drink.id
            break_row.version += 1
        session.version += 1

    db.commit()
    db.refresh(drink)
    return _drink_response(drink)


def update_drink(db: Session, user: PaceUser, drink_id: UUID, payload: AlcoholDrinkUpdate):
    row = repo.get_drink(db, user.id, drink_id)
    if row is None:
        _not_found("Drink")
    if not payload.model_dump(exclude_unset=True):
        return _drink_response(row)
    session = repo.get_session(db, user.id, row.session_id)
    if session is None:
        _not_found("Alcohol session")
    changes = payload.model_dump(exclude_unset=True)
    if session.entry_mode == "live" and "logged_at" in changes and changes["logged_at"] is not None:
        if _is_before(changes["logged_at"], session.started_at):
            raise HTTPException(status_code=422, detail="Drink time cannot be earlier than session start")
    return _drink_response(repo.update_drink(db, row, payload))


def delete_drink(db: Session, user: PaceUser, drink_id: UUID):
    row = repo.get_drink(db, user.id, drink_id)
    if row is None:
        _not_found("Drink")
    repo.soft_delete(db, row)


def add_water(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholWaterCreate):
    session = repo.get_session(db, user.id, session_id)
    if session is None:
        _not_found("Alcohol session")
    event_time = payload.logged_at or (_now() if session.entry_mode == "live" else None)
    if session.entry_mode == "live" and _is_before(event_time, session.started_at):
        raise HTTPException(status_code=422, detail="Water time cannot be earlier than session start")
    normalized = payload.model_copy(update={"logged_at": event_time})
    return _water_response(repo.create_water_entry(db, user.id, session.id, normalized))


def update_water(db: Session, user: PaceUser, entry_id: UUID, payload: AlcoholWaterUpdate):
    row = repo.get_water_entry(db, user.id, entry_id)
    if row is None:
        _not_found("Water entry")
    if not payload.model_dump(exclude_unset=True):
        return _water_response(row)
    return _water_response(repo.update_water_entry(db, row, payload))


def delete_water(db: Session, user: PaceUser, entry_id: UUID):
    row = repo.get_water_entry(db, user.id, entry_id)
    if row is None:
        _not_found("Water entry")
    repo.soft_delete(db, row)


def add_break(db: Session, user: PaceUser, session_id: UUID, payload: AlcoholBreakCreate):
    session = repo.get_session(db, user.id, session_id)
    if session is None:
        _not_found("Alcohol session")
    if session.entry_mode != "live" or session.status != "active":
        raise HTTPException(status_code=409, detail="Breaks can only be added to an active live session")
    if repo.get_running_breaks(db, user.id, session.id):
        raise HTTPException(status_code=409, detail="A break is already running")
    started_at = payload.started_at or _now()
    if _is_before(started_at, session.started_at):
        raise HTTPException(status_code=422, detail="Break cannot start before the session")
    return _break_response(repo.create_break(db, user.id, session.id, payload, started_at))


def update_break(db: Session, user: PaceUser, break_id: UUID, payload: AlcoholBreakUpdate):
    row = repo.get_break(db, user.id, break_id)
    if row is None:
        _not_found("Break")
    if not payload.model_dump(exclude_unset=True):
        return _break_response(row)
    changes = payload.model_dump(exclude_unset=True)
    ended_at = changes.get("ended_at")
    if ended_at is not None and _is_before(ended_at, row.started_at):
        raise HTTPException(status_code=422, detail="Break end cannot be earlier than break start")
    if changes.get("status") in {"completed", "cancelled"} and ended_at is None and row.ended_at is None:
        payload = payload.model_copy(update={"ended_at": _now()})
    return _break_response(repo.update_break(db, row, payload))


def delete_break(db: Session, user: PaceUser, break_id: UUID):
    row = repo.get_break(db, user.id, break_id)
    if row is None:
        _not_found("Break")
    repo.soft_delete(db, row)


def create_favorite(db: Session, user: PaceUser, payload: AlcoholFavoriteCreate):
    return _favorite_response(repo.create_favorite(db, user.id, payload))


def list_favorites(db: Session, user: PaceUser):
    return [_favorite_response(row) for row in repo.list_favorites(db, user.id)]


def get_favorite(db: Session, user: PaceUser, favorite_id: UUID):
    row = repo.get_favorite(db, user.id, favorite_id)
    if row is None:
        _not_found("Favorite")
    return _favorite_response(row)


def update_favorite(db: Session, user: PaceUser, favorite_id: UUID, payload: AlcoholFavoriteUpdate):
    row = repo.get_favorite(db, user.id, favorite_id)
    if row is None:
        _not_found("Favorite")
    if not payload.model_dump(exclude_unset=True):
        return _favorite_response(row)
    return _favorite_response(repo.update_favorite(db, row, payload))


def delete_favorite(db: Session, user: PaceUser, favorite_id: UUID):
    row = repo.get_favorite(db, user.id, favorite_id)
    if row is None:
        _not_found("Favorite")
    repo.soft_delete(db, row)


def log_favorite(db: Session, user: PaceUser, favorite_id: UUID, payload: AlcoholFavoriteLog):
    favorite = repo.get_favorite(db, user.id, favorite_id)
    if favorite is None:
        _not_found("Favorite")
    session = repo.get_session(db, user.id, payload.session_id)
    if session is None:
        _not_found("Alcohol session")
    drink_payload = AlcoholDrinkCreate(
        category=favorite.category,
        name=favorite.name,
        brand=favorite.brand,
        volume_ml=float(favorite.volume_ml),
        abv_percent=float(favorite.abv_percent),
        logged_at=payload.logged_at,
        client_updated_at=payload.client_updated_at,
    )
    drink = add_drink(db, user, session.id, drink_payload)
    used_at = drink.logged_at or _now()
    favorite.usage_count += 1
    favorite.last_used_at = used_at
    favorite.client_updated_at = payload.client_updated_at
    favorite.version += 1
    db.commit()
    return drink
