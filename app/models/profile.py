import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PaceProfile(TimestampMixin, Base):
    __tablename__ = "pace_profiles"
    __table_args__ = (
        CheckConstraint("height_cm > 0", name="ck_pace_profiles_height_positive"),
        CheckConstraint("weight_kg > 0", name="ck_pace_profiles_weight_positive"),
        CheckConstraint(
            "training_days_per_week >= 0 AND training_days_per_week <= 6",
            name="ck_pace_profiles_training_days_range",
        ),
        CheckConstraint(
            "calorie_estimate_sex IN ('male', 'female', 'neutral')",
            name="ck_pace_profiles_calorie_estimate_sex",
        ),
        CheckConstraint(
            "goal IN ('lose_body_fat', 'maintain', 'build_muscle', 'improve_performance', 'general_health')",
            name="ck_pace_profiles_goal",
        ),
        CheckConstraint(
            "activity_level IN ('mostly_sedentary', 'lightly_active', 'active', 'very_active')",
            name="ck_pace_profiles_activity_level",
        ),
        CheckConstraint(
            "training_experience IN ('beginner', 'intermediate', 'experienced')",
            name="ck_pace_profiles_training_experience",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pace_users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    calorie_estimate_sex: Mapped[str] = mapped_column(String(16), nullable=False)
    goal: Mapped[str] = mapped_column(String(32), nullable=False)
    activity_level: Mapped[str] = mapped_column(String(32), nullable=False)
    training_experience: Mapped[str] = mapped_column(String(32), nullable=False)
    training_days_per_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("PaceUser", back_populates="profile")
