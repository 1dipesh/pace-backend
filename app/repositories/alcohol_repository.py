from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alcohol import (
    AlcoholBreak,
    AlcoholDrink,
    AlcoholFavorite,
    AlcoholSession,
    AlcoholWaterEntry,
)
from app.schemas.alcohol import (
    AlcoholBreakCreate,
    AlcoholBreakUpdate,
    AlcoholDrinkCreate,
    AlcoholDrinkUpdate,
    AlcoholFavoriteCreate,
    AlcoholFavoriteUpdate,
    AlcoholSessionUpdate,
    AlcoholWaterCreate,
    AlcoholWaterUpdate,
)

ETHANOL_DENSITY_G_PER_ML = Decimal("0.789")


def calculate_alcohol_grams(volume_ml: float | Decimal, abv_percent: float | Decimal) -> Decimal:
    volume = Decimal(str(volume_ml))
    abv = Decimal(str(abv_percent))
    grams = volume * (abv / Decimal("100")) * ETHANOL_DENSITY_G_PER_ML
    return grams.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def get_active_live_session(db: Session, user_id: UUID):
    return db.scalar(
        select(AlcoholSession)
        .where(
            AlcoholSession.user_id == user_id,
            AlcoholSession.entry_mode == "live",
            AlcoholSession.status == "active",
            AlcoholSession.deleted_at.is_(None),
        )
        .order_by(AlcoholSession.started_at.desc())
        .limit(1)
    )


def create_session(
    db: Session,
    user_id: UUID,
    *,
    entry_mode: str,
    session_date: date,
    started_at: datetime | None,
    ended_at: datetime | None,
    notes: str | None,
    client_updated_at: datetime | None,
):
    row = AlcoholSession(
        user_id=user_id,
        entry_mode=entry_mode,
        status="active" if entry_mode == "live" and ended_at is None else "completed",
        session_date=session_date,
        started_at=started_at,
        ended_at=ended_at,
        total_paused_seconds=0,
        notes=notes,
        client_updated_at=client_updated_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_session(db: Session, user_id: UUID, session_id: UUID):
    return db.scalar(
        select(AlcoholSession).where(
            AlcoholSession.id == session_id,
            AlcoholSession.user_id == user_id,
            AlcoholSession.deleted_at.is_(None),
        )
    )


def list_sessions(
    db: Session,
    user_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    entry_mode: str | None = None,
    session_status: str | None = None,
    limit: int = 100,
):
    stmt = select(AlcoholSession).where(
        AlcoholSession.user_id == user_id,
        AlcoholSession.deleted_at.is_(None),
    )
    if from_date is not None:
        stmt = stmt.where(AlcoholSession.session_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(AlcoholSession.session_date <= to_date)
    if entry_mode is not None:
        stmt = stmt.where(AlcoholSession.entry_mode == entry_mode)
    if session_status is not None:
        stmt = stmt.where(AlcoholSession.status == session_status)
    return list(
        db.scalars(stmt.order_by(AlcoholSession.session_date.desc(), AlcoholSession.created_at.desc()).limit(limit)).all()
    )


def update_session(db: Session, row: AlcoholSession, payload: AlcoholSessionUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def save_session(db: Session, row: AlcoholSession):
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def list_drinks(db: Session, user_id: UUID, session_id: UUID):
    return list(
        db.scalars(
            select(AlcoholDrink)
            .where(
                AlcoholDrink.user_id == user_id,
                AlcoholDrink.session_id == session_id,
                AlcoholDrink.deleted_at.is_(None),
            )
            .order_by(AlcoholDrink.logged_at.asc().nulls_last(), AlcoholDrink.created_at.asc())
        ).all()
    )


def get_drink(db: Session, user_id: UUID, drink_id: UUID):
    return db.scalar(
        select(AlcoholDrink).where(
            AlcoholDrink.id == drink_id,
            AlcoholDrink.user_id == user_id,
            AlcoholDrink.deleted_at.is_(None),
        )
    )


def create_drink(db: Session, user_id: UUID, session_id: UUID, payload: AlcoholDrinkCreate):
    grams = calculate_alcohol_grams(payload.volume_ml, payload.abv_percent)
    row = AlcoholDrink(
        user_id=user_id,
        session_id=session_id,
        alcohol_grams=grams,
        **payload.model_dump(),
    )
    db.add(row)
    db.flush()
    return row


def update_drink(db: Session, row: AlcoholDrink, payload: AlcoholDrinkUpdate):
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(row, field, value)
    if "volume_ml" in changes or "abv_percent" in changes:
        row.alcohol_grams = calculate_alcohol_grams(row.volume_ml, row.abv_percent)
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def list_water_entries(db: Session, user_id: UUID, session_id: UUID):
    return list(
        db.scalars(
            select(AlcoholWaterEntry)
            .where(
                AlcoholWaterEntry.user_id == user_id,
                AlcoholWaterEntry.session_id == session_id,
                AlcoholWaterEntry.deleted_at.is_(None),
            )
            .order_by(AlcoholWaterEntry.logged_at.asc().nulls_last(), AlcoholWaterEntry.created_at.asc())
        ).all()
    )


def get_water_entry(db: Session, user_id: UUID, entry_id: UUID):
    return db.scalar(
        select(AlcoholWaterEntry).where(
            AlcoholWaterEntry.id == entry_id,
            AlcoholWaterEntry.user_id == user_id,
            AlcoholWaterEntry.deleted_at.is_(None),
        )
    )


def create_water_entry(db: Session, user_id: UUID, session_id: UUID, payload: AlcoholWaterCreate):
    row = AlcoholWaterEntry(user_id=user_id, session_id=session_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_water_entry(db: Session, row: AlcoholWaterEntry, payload: AlcoholWaterUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def list_breaks(db: Session, user_id: UUID, session_id: UUID):
    return list(
        db.scalars(
            select(AlcoholBreak)
            .where(
                AlcoholBreak.user_id == user_id,
                AlcoholBreak.session_id == session_id,
                AlcoholBreak.deleted_at.is_(None),
            )
            .order_by(AlcoholBreak.started_at.asc())
        ).all()
    )


def get_break(db: Session, user_id: UUID, break_id: UUID):
    return db.scalar(
        select(AlcoholBreak).where(
            AlcoholBreak.id == break_id,
            AlcoholBreak.user_id == user_id,
            AlcoholBreak.deleted_at.is_(None),
        )
    )


def create_break(db: Session, user_id: UUID, session_id: UUID, payload: AlcoholBreakCreate, started_at: datetime):
    row = AlcoholBreak(
        user_id=user_id,
        session_id=session_id,
        planned_duration_seconds=payload.planned_duration_seconds,
        status="running",
        started_at=started_at,
        client_updated_at=payload.client_updated_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_break(db: Session, row: AlcoholBreak, payload: AlcoholBreakUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def get_running_breaks(db: Session, user_id: UUID, session_id: UUID):
    return list(
        db.scalars(
            select(AlcoholBreak).where(
                AlcoholBreak.user_id == user_id,
                AlcoholBreak.session_id == session_id,
                AlcoholBreak.status == "running",
                AlcoholBreak.deleted_at.is_(None),
            )
        ).all()
    )


def list_favorites(db: Session, user_id: UUID):
    return list(
        db.scalars(
            select(AlcoholFavorite)
            .where(AlcoholFavorite.user_id == user_id, AlcoholFavorite.deleted_at.is_(None))
            .order_by(AlcoholFavorite.usage_count.desc(), AlcoholFavorite.name.asc())
        ).all()
    )


def get_favorite(db: Session, user_id: UUID, favorite_id: UUID):
    return db.scalar(
        select(AlcoholFavorite).where(
            AlcoholFavorite.id == favorite_id,
            AlcoholFavorite.user_id == user_id,
            AlcoholFavorite.deleted_at.is_(None),
        )
    )


def create_favorite(db: Session, user_id: UUID, payload: AlcoholFavoriteCreate):
    row = AlcoholFavorite(user_id=user_id, usage_count=0, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_favorite(db: Session, row: AlcoholFavorite, payload: AlcoholFavoriteUpdate):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.version += 1
    db.commit()
    db.refresh(row)
    return row


def soft_delete(db: Session, row) -> None:
    row.deleted_at = datetime.now(timezone.utc)
    row.version += 1
    db.commit()


def soft_delete_session_graph(db: Session, user_id: UUID, row: AlcoholSession) -> None:
    now = datetime.now(timezone.utc)
    children = [
        *list_drinks(db, user_id, row.id),
        *list_water_entries(db, user_id, row.id),
        *list_breaks(db, user_id, row.id),
    ]
    for child in children:
        child.deleted_at = now
        child.version += 1
    row.deleted_at = now
    row.version += 1
    db.commit()
