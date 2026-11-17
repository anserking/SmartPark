from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NavigationSession(Base):
    __tablename__ = "navigation_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    destination_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("destinations.id"), nullable=False
    )
    parking_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("parking_spots.id", ondelete="SET NULL")
    )
    vehicle_type: Mapped[str] = mapped_column(String(20), nullable=False)
    navigation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    parked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
