import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.destination import CoordinateResponse
from app.schemas.parking import ParkingFacilityResponse, ParkingSearchResponse
from app.services.geography import validate_coordinate
from app.services.overpass import OverpassClient, overpass_client
from app.services.parking_normalization import NormalizedParking
from app.services.providers import GeographicProviderError

router = APIRouter(prefix="/api/parking", tags=["parking"])


def get_overpass_client() -> OverpassClient:
    return overpass_client


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


@router.get("/search", response_model=ParkingSearchResponse)
async def search_parking(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius_meters: Annotated[int, Query(ge=100, le=50000)] = 1500,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    provider: OverpassClient = Depends(get_overpass_client),
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
                detail="OpenStreetMap parking search rate limit reached",
                headers=headers,
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="OpenStreetMap parking data is unavailable",
        ) from exc

    results = [
        result
        for facility in facilities
        if (result := _response(facility, latitude, longitude)) is not None
    ]
    results.sort(key=lambda result: (result.straight_line_distance_meters, result.id))
    return ParkingSearchResponse(results=results[:limit])
