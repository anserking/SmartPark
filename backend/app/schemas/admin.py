from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.destination import CoordinateResponse


AvailabilityStatus = Literal["verified", "unverified", "unavailable", "unknown"]
VerificationStatus = Literal["verified", "unverified"]


class ParkingSpotWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    location: CoordinateResponse
    parking_type: str | None = Field(default=None, alias="parkingType", max_length=80)
    hourly_fee: Decimal | None = Field(default=None, alias="hourlyFee", ge=0)
    supports_car: bool | None = Field(default=None, alias="supportsCar")
    supports_bike: bool | None = Field(default=None, alias="supportsBike")
    capacity: int | None = Field(default=None, ge=0)
    available_spaces: int | None = Field(default=None, alias="availableSpaces", ge=0)
    availability_status: AvailabilityStatus = Field(
        default="unknown", alias="availabilityStatus"
    )
    verification_status: VerificationStatus = Field(
        default="unverified", alias="verificationStatus"
    )


class ParkingSpotUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str | None = Field(default=None, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    location: CoordinateResponse | None = None
    parking_type: str | None = Field(default=None, alias="parkingType", max_length=80)
    hourly_fee: Decimal | None = Field(default=None, alias="hourlyFee", ge=0)
    supports_car: bool | None = Field(default=None, alias="supportsCar")
    supports_bike: bool | None = Field(default=None, alias="supportsBike")
    capacity: int | None = Field(default=None, ge=0)
    available_spaces: int | None = Field(default=None, alias="availableSpaces", ge=0)
    availability_status: AvailabilityStatus | None = Field(
        default=None, alias="availabilityStatus"
    )
    verification_status: VerificationStatus | None = Field(
        default=None, alias="verificationStatus"
    )


class AdminParkingSpotResponse(BaseModel):
    id: UUID
    name: str | None
    address: str | None
    location: CoordinateResponse
    parking_type: str | None = Field(serialization_alias="parkingType")
    hourly_fee: float | None = Field(serialization_alias="hourlyFee")
    supports_car: bool | None = Field(serialization_alias="supportsCar")
    supports_bike: bool | None = Field(serialization_alias="supportsBike")
    capacity: int | None
    available_spaces: int | None = Field(serialization_alias="availableSpaces")
    availability_status: AvailabilityStatus = Field(
        serialization_alias="availabilityStatus"
    )
    verification_status: VerificationStatus = Field(
        serialization_alias="verificationStatus"
    )
    source: str
