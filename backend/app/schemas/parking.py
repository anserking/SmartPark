from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.destination import CoordinateResponse


class ParkingFacilityResponse(BaseModel):
    id: str
    name: str | None
    address: str | None
    location: CoordinateResponse
    parking_type: str = Field(serialization_alias="parkingType")
    fee: str | None
    capacity: int | None
    supports_car: bool | None = Field(serialization_alias="supportsCar")
    supports_bike: bool | None = Field(serialization_alias="supportsBike")
    straight_line_distance_meters: float = Field(
        ge=0, serialization_alias="straightLineDistanceMeters"
    )
    availability_status: Literal["unknown"] = Field(
        default="unknown", serialization_alias="availabilityStatus"
    )
    verification_status: Literal["unverified"] = Field(
        default="unverified", serialization_alias="verificationStatus"
    )
    source: Literal["openstreetmap"] = "openstreetmap"


class ParkingSearchResponse(BaseModel):
    results: list[ParkingFacilityResponse]
