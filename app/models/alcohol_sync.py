from sqlalchemy import ForeignKey, JSON, String, Uuid, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from app.db.base import Base


class AlcoholSyncRecord(Base):
    __tablename__ = "alcohol_sync_records"
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("pace_users.id", ondelete="CASCADE"), primary_key=True)
    entity: Mapped[str] = mapped_column(String(16), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)
