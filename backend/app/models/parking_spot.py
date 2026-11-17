from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParkingSpot(Base):
    __tablename__ = "parking_spots"
    __table_args__ = (
        CheckConstraint(
            "availability_status IN ('verified', 'unverified', 'unavailable', 'unknown')",
            name="availability_status",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'unverified')",
            name="verification_status",
        ),
        CheckConstraint("capacity IS NULL OR capacity >= 0", name="capacity_nonnegative"),
        CheckConstraint(
            "available_spaces IS NULL OR available_spaces >= 0",
            name="available_spaces_nonnegative",
        ),
        CheckConstraint("hourly_fee IS NULL OR hourly_fee >= 0", name="hourly_fee_nonnegative"),
        Index("ix_parking_spots_location_gist", "location", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
        nullable=False,
    )
    osm_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="osm")
    parking_type: Mapped[str | None] = mapped_column(String(80))
    hourly_fee: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    supports_car: Mapped[bool | None] = mapped_column(Boolean)
    supports_bike: Mapped[bool | None] = mapped_column(Boolean)
    capacity: Mapped[int | None] = mapped_column(Integer)
    available_spaces: Mapped[int | None] = mapped_column(Integer)
    availability_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="unknown"
    )
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="unverified"
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
