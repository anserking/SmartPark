from decimal import Decimal
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
    source: Literal["google_maps"] = "google_maps"


class ParkingSearchResponse(BaseModel):
    results: list[ParkingFacilityResponse]


class ParkingRecommendationResponse(BaseModel):
    id: str
    name: str | None
    address: str | None
    location: CoordinateResponse
    parking_type: str = Field(serialization_alias="parkingType")
    fee: str | None
    hourly_fee: float | None = Field(serialization_alias="hourlyFee")
    capacity: int | None
    supports_car: bool | None = Field(serialization_alias="supportsCar")
    supports_bike: bool | None = Field(serialization_alias="supportsBike")
    destination_distance_meters: float = Field(
        ge=0, serialization_alias="destinationDistanceMeters"
    )
    destination_distance_method: Literal["road", "straight_line"] = Field(
        serialization_alias="destinationDistanceMethod"
    )
    user_distance_meters: float | None = Field(
        default=None, ge=0, serialization_alias="userDistanceMeters"
    )
    availability_status: Literal[
        "verified", "unverified", "unavailable", "unknown"
    ] = Field(serialization_alias="availabilityStatus")
    verification_status: Literal["verified", "unverified"] = Field(
        serialization_alias="verificationStatus"
    )
    source: str


class ParkingRecommendationSearchResponse(BaseModel):
    results: list[ParkingRecommendationResponse]
    distance_method: Literal["road", "straight_line"] = Field(
        serialization_alias="distanceMethod"
    )
