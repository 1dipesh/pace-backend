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
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class CardioActivity(TimestampMixin, Base):
    __tablename__ = "cardio_activities"
    __table_args__ = (
        CheckConstraint(
            "activity_type IN ('running', 'walking', 'cycling', 'football', 'basketball', 'rowing', 'swimming', 'other')",
            name="ck_cardio_activities_type",
        ),
        CheckConstraint("duration_seconds > 0", name="ck_cardio_activities_duration"),
        CheckConstraint("distance_km IS NULL OR distance_km >= 0", name="ck_cardio_activities_distance"),
        Index("ix_cardio_activities_user_date", "user_id", "activity_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_type: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HybridSession(TimestampMixin, Base):
    __tablename__ = "hybrid_sessions"
    __table_args__ = (
        CheckConstraint(
            "session_type IN ('hyrox_full', 'hyrox_half', 'hyrox_stations_only', 'custom')",
            name="ck_hybrid_sessions_type",
        ),
        CheckConstraint(
            "total_duration_seconds IS NULL OR total_duration_seconds >= 0",
            name="ck_hybrid_sessions_duration",
        ),
        Index("ix_hybrid_sessions_user_started", "user_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_type: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class HybridSegment(TimestampMixin, Base):
    __tablename__ = "hybrid_segments"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_hybrid_segments_position"),
        CheckConstraint("segment_type IN ('run', 'station')", name="ck_hybrid_segments_type"),
        CheckConstraint(
            "target_distance_m IS NULL OR target_distance_m >= 0",
            name="ck_hybrid_segments_target_distance",
        ),
        CheckConstraint("target_reps IS NULL OR target_reps >= 0", name="ck_hybrid_segments_target_reps"),
        CheckConstraint("load IS NULL OR load >= 0", name="ck_hybrid_segments_load"),
        CheckConstraint("load_unit IS NULL OR load_unit IN ('kg', 'lb')", name="ck_hybrid_segments_load_unit"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_hybrid_segments_duration",
        ),
        Index("ix_hybrid_segments_session_position", "session_id", "position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pace_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hybrid_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    segment_type: Mapped[str] = mapped_column(String(8), nullable=False)
    segment_name: Mapped[str] = mapped_column(String(160), nullable=False)
    station_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_distance_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    load: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    load_unit: Mapped[str | None] = mapped_column(String(4), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
