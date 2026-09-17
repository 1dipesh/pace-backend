import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PaceUser(TimestampMixin, Base):
    __tablename__ = "pace_users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), index=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    ai_plan: Mapped[str] = mapped_column(String(20), default="beta", server_default="beta", nullable=False)

    profile = relationship(
        "PaceProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
