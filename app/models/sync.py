from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SyncReceipt(Base):
    __tablename__ = "pace_sync_receipts"
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("pace_users.id", ondelete="CASCADE"), primary_key=True)
    mutation_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
