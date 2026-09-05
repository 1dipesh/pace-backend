import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class AlcoholSession(TimestampMixin, Base):
    __tablename__ = "alcohol_sessions"
    __table_args__ = (
        CheckConstraint("entry_mode IN ('live', 'historical')", name="ck_alcohol_sessions_entry_mode"),
        CheckConstraint("status IN ('active', 'completed')", name="ck_alcohol_sessions_status"),
        CheckConstraint("total_paused_seconds >= 0", name="ck_alcohol_sessions_paused_nonnegative"),
        CheckConstraint(
            "(entry_mode = 'live' AND started_at IS NOT NULL) OR "
            "(entry_mode = 'historical' AND started_at IS NULL AND status = 'completed')",
            name="ck_alcohol_sessions_mode_timing",
        ),
        Index("ix_alcohol_sessions_user_date", "user_id", "session_date"),
        Index("ix_alcohol_sessions_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_mode: Mapped[str] = mapped_column(String(12), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_paused_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlcoholDrink(TimestampMixin, Base):
    __tablename__ = "alcohol_drinks"
    __table_args__ = (
        CheckConstraint(
            "category IN ('beer', 'wine', 'spirits', 'cocktail', 'other')",
            name="ck_alcohol_drinks_category",
        ),
        CheckConstraint("volume_ml > 0", name="ck_alcohol_drinks_volume_positive"),
        CheckConstraint("abv_percent >= 0 AND abv_percent <= 100", name="ck_alcohol_drinks_abv_range"),
        CheckConstraint("alcohol_grams >= 0", name="ck_alcohol_drinks_grams_nonnegative"),
        Index("ix_alcohol_drinks_session_logged", "session_id", "logged_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alcohol_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    volume_ml: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    abv_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    alcohol_grams: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlcoholWaterEntry(TimestampMixin, Base):
    __tablename__ = "alcohol_water_entries"
    __table_args__ = (
        CheckConstraint("volume_ml IS NULL OR volume_ml > 0", name="ck_alcohol_water_entries_volume_positive"),
        Index("ix_alcohol_water_entries_session_logged", "session_id", "logged_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alcohol_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    volume_ml: Mapped[int | None] = mapped_column(Integer, nullable=True)
    container: Mapped[str | None] = mapped_column(String(80), nullable=True)
    logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlcoholBreak(TimestampMixin, Base):
    __tablename__ = "alcohol_breaks"
    __table_args__ = (
        CheckConstraint("planned_duration_seconds > 0", name="ck_alcohol_breaks_duration_positive"),
        CheckConstraint(
            "status IN ('running', 'completed', 'interrupted', 'cancelled')",
            name="ck_alcohol_breaks_status",
        ),
        Index("ix_alcohol_breaks_session_started", "session_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alcohol_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    planned_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="running", server_default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interrupted_by_drink_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("alcohol_drinks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlcoholFavorite(TimestampMixin, Base):
    __tablename__ = "alcohol_favorites"
    __table_args__ = (
        CheckConstraint(
            "category IN ('beer', 'wine', 'spirits', 'cocktail', 'other')",
            name="ck_alcohol_favorites_category",
        ),
        CheckConstraint("volume_ml > 0", name="ck_alcohol_favorites_volume_positive"),
        CheckConstraint("abv_percent >= 0 AND abv_percent <= 100", name="ck_alcohol_favorites_abv_range"),
        CheckConstraint("usage_count >= 0", name="ck_alcohol_favorites_usage_nonnegative"),
        Index("ix_alcohol_favorites_user_name", "user_id", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(12), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(160), nullable=True)
    volume_ml: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    abv_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
