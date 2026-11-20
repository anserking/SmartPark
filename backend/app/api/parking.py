import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.parking_spot import ParkingSpot
from app.schemas.destination import CoordinateResponse
from app.schemas.parking import (
    ParkingFacilityResponse,
    ParkingRecommendationResponse,
    ParkingRecommendationSearchResponse,
    ParkingSearchResponse,
)
from app.services.geography import validate_coordinate
from app.services.google_places import GooglePlacesClient
from app.services.parking_normalization import NormalizedParking
from app.services.parking_recommendations import (
    ParkingRecommendationCandidate,
    RankedRecommendation,
    rank_parking_recommendations,
)
from app.services.providers import GeographicProviderError

router = APIRouter(prefix="/api/parking", tags=["parking"])


@dataclass(frozen=True, slots=True)
class _ParkingDetails:
    candidate: ParkingRecommendationCandidate
    name: str | None
    address: str | None
    parking_type: str
    fee: str | None
    capacity: int | None
    availability_status: Literal["verified", "unverified", "unavailable", "unknown"]
    verification_status: Literal["verified", "unverified"]
    source: str


def get_google_places_client() -> GooglePlacesClient:
    return GooglePlacesClient()


def _straight_line_distance_meters(
    origin_latitude: float,
    origin_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> float:
    earth_radius_meters = 6_371_000
    origin_latitude_radians = math.radians(origin_latitude)
    destination_latitude_radians = math.radians(destination_latitude)
    latitude_delta = math.radians(destination_latitude - origin_latitude)
    longitude_delta = math.radians(destination_longitude - origin_longitude)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(origin_latitude_radians)
        * math.cos(destination_latitude_radians)
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_meters * math.asin(math.sqrt(haversine))


def _address(tags: dict[str, str]) -> str | None:
    full_address = tags.get("addr:full")
    if full_address:
        return full_address

    parts = (
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
    )
    address = ", ".join(dict.fromkeys(part.strip() for part in parts if part and part.strip()))
    return address or None


def _response(
    facility: NormalizedParking,
    latitude: float,
    longitude: float,
) -> ParkingFacilityResponse | None:
    if facility.geometry.get("type") != "Point":
        return None
    coordinates = facility.geometry.get("coordinates")
    if (
        not isinstance(coordinates, list)
        or len(coordinates) != 2
    ):
        return None

    try:
        facility_longitude, facility_latitude = validate_coordinate(
            coordinates[0], coordinates[1]
        )
    except ValueError:
        return None

    return ParkingFacilityResponse(
        id=facility.osm_id,
        name=facility.name,
        address=_address(facility.tags),
        location=CoordinateResponse(
            latitude=facility_latitude,
            longitude=facility_longitude,
        ),
        parking_type=facility.parking_type,
        fee=facility.fee,
        capacity=facility.capacity,
        supports_car=facility.supports_car,
        supports_bike=facility.supports_bike,
        straight_line_distance_meters=_straight_line_distance_meters(
            latitude,
            longitude,
            facility_latitude,
            facility_longitude,
        ),
    )


def _recommendation_response(
    ranked: RankedRecommendation,
    details: _ParkingDetails,
    user_latitude: float | None,
    user_longitude: float | None,
) -> ParkingRecommendationResponse:
    candidate = details.candidate
    user_distance = (
        _straight_line_distance_meters(
            user_latitude,
            user_longitude,
            candidate.latitude,
            candidate.longitude,
        )
        if user_latitude is not None and user_longitude is not None
        else None
    )
    return ParkingRecommendationResponse(
        id=candidate.id,
        name=details.name,
        address=details.address,
        location=CoordinateResponse(
            latitude=candidate.latitude,
            longitude=candidate.longitude,
        ),
        parking_type=details.parking_type,
        fee=details.fee,
        hourly_fee=(
            float(candidate.hourly_fee)
            if candidate.hourly_fee is not None
            else None
        ),
        capacity=details.capacity,
        supports_car=candidate.supports_car,
        supports_bike=candidate.supports_bike,
        destination_distance_meters=ranked.destination_distance_meters,
        destination_distance_method=ranked.distance_method,
        user_distance_meters=user_distance,
        availability_status=details.availability_status,
        verification_status=details.verification_status,
        source=details.source,
    )


@router.get(
    "/recommendations",
    response_model=ParkingRecommendationSearchResponse,
)
async def recommend_parking(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    vehicle_type: Annotated[Literal["car", "bike"], Query()] = "car",
    radius_meters: Annotated[int, Query(ge=100, le=50000)] = 2000,
    limit: Annotated[int, Query(ge=1, le=5)] = 5,
    destination_name: Annotated[str | None, Query(min_length=2, max_length=150)] = None,
    user_latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    user_longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    db: Session = Depends(get_db),
    provider: GooglePlacesClient = Depends(get_google_places_client),
) -> ParkingRecommendationSearchResponse:
    if (user_latitude is None) != (user_longitude is None):
        raise HTTPException(
            status_code=422,
            detail="User latitude and longitude must be provided together",
        )

    try:
        facilities = await provider.nearby_parking(
            latitude,
            longitude,
            radius_meters=radius_meters,
            destination_name=destination_name,
        )
    except GeographicProviderError as exc:
        if exc.status_code == 429:
            headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
            raise HTTPException(
                status_code=429,
                detail="Google parking search rate limit reached",
                headers=headers,
            ) from exc
        raise HTTPException(
            status_code=503 if exc.status_code == 503 else 502,
            detail="Google parking data is unavailable",
        ) from exc

    details_by_id: dict[str, _ParkingDetails] = {}
    for facility in facilities:
        response = _response(facility, latitude, longitude)
        if response is None:
            continue
        candidate = ParkingRecommendationCandidate(
            id=response.id,
            latitude=response.location.latitude,
            longitude=response.location.longitude,
            supports_car=response.supports_car,
            supports_bike=response.supports_bike,
            hourly_fee=None,
        )
        details_by_id[response.id] = _ParkingDetails(
            candidate=candidate,
            name=response.name,
            address=response.address,
            parking_type=response.parking_type,
            fee=response.fee,
            capacity=response.capacity,
            availability_status="unknown",
            verification_status="unverified",
            source=facility.source,
        )

    for spot in db.scalars(select(ParkingSpot)).all():
        if spot.source != "admin":
            continue
        point = to_shape(spot.location)
        if point.geom_type != "Point":
            point = point.representative_point()
        spot_latitude, spot_longitude = point.y, point.x
        if (
            _straight_line_distance_meters(
                latitude,
                longitude,
                spot_latitude,
                spot_longitude,
            )
            > radius_meters
        ):
            continue

        spot_id = spot.osm_id or str(spot.id)
        if spot.availability_status == "unavailable":
            details_by_id.pop(spot_id, None)
            continue
        hourly_fee = (
            Decimal(spot.hourly_fee)
            if spot.hourly_fee is not None
            else None
        )
        candidate = ParkingRecommendationCandidate(
            id=spot_id,
            latitude=spot_latitude,
            longitude=spot_longitude,
            supports_car=spot.supports_car,
            supports_bike=spot.supports_bike,
            hourly_fee=hourly_fee,
        )
        details_by_id[spot_id] = _ParkingDetails(
            candidate=candidate,
            name=spot.name,
            address=spot.address,
            parking_type=spot.parking_type or "parking",
            fee=f"PKR {hourly_fee}/hour" if hourly_fee is not None else None,
            capacity=spot.capacity,
            availability_status=spot.availability_status,
            verification_status=spot.verification_status,
            source=spot.source,
        )

    candidate_details = list(details_by_id.values())
    for nearby_radius in (300, 600, 1000, 2000, radius_meters):
        if nearby_radius > radius_meters:
            continue
        close_details = [
            details for details in candidate_details
            if (details.candidate.supports_car if vehicle_type == "car"
                else details.candidate.supports_bike) is not False
            if _straight_line_distance_meters(
                latitude, longitude,
                details.candidate.latitude, details.candidate.longitude,
            ) <= nearby_radius
        ]
        if close_details:
            candidate_details = close_details
            break

    ranked = rank_parking_recommendations(
        destination_latitude=latitude,
        destination_longitude=longitude,
        candidates=[
            details.candidate for details in candidate_details
        ],
        vehicle_type=vehicle_type,
        node_locations={},
        edges=[],
        max_results=limit,
    )
    distance_method = ranked[0].distance_method if ranked else "straight_line"
    return ParkingRecommendationSearchResponse(
        results=[
            _recommendation_response(
                recommendation,
                details_by_id[recommendation.candidate.id],
                user_latitude,
                user_longitude,
            )
            for recommendation in ranked
        ],
        distance_method=distance_method,
    )


@router.get("/search", response_model=ParkingSearchResponse)
async def search_parking(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius_meters: Annotated[int, Query(ge=100, le=50000)] = 1500,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    provider: GooglePlacesClient = Depends(get_google_places_client),
) -> ParkingSearchResponse:
    try:
        facilities = await provider.nearby_parking(
            latitude,
            longitude,
            radius_meters=radius_meters,
        )
    except GeographicProviderError as exc:
        if exc.status_code == 429:
            headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
            raise HTTPException(
                status_code=429,
                detail="Google parking search rate limit reached",
                headers=headers,
            ) from exc
        raise HTTPException(
            status_code=503 if exc.status_code == 503 else 502,
            detail="Google parking data is unavailable",
        ) from exc

    results = [
        result
        for facility in facilities
        if (result := _response(facility, latitude, longitude)) is not None
    ]
    results.sort(key=lambda result: (result.straight_line_distance_meters, result.id))
    return ParkingSearchResponse(results=results[:limit])
