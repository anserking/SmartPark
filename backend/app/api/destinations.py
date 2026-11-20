from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geometry
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.destination import Destination
from app.schemas.destination import (
    CoordinateResponse,
    DestinationResponse,
    DestinationSearchResponse,
)
from app.services.google_places import GooglePlacesClient
from app.services.providers import GeographicProviderError

router = APIRouter(prefix="/api/destinations", tags=["destinations"])


def get_geocoder() -> GooglePlacesClient:
    return GooglePlacesClient()


@router.get("/search", response_model=DestinationSearchResponse)
async def search_destinations(
    q: str = Query(min_length=2, max_length=150),
    limit: int = Query(default=5, ge=1, le=10),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    provider: GooglePlacesClient = Depends(get_geocoder),
) -> DestinationSearchResponse:
    query = " ".join(q.split())
    if len(query) < 2:
        raise HTTPException(status_code=422, detail="Search query must contain at least two characters")
    if (latitude is None) != (longitude is None):
        raise HTTPException(
            status_code=422,
            detail="Latitude and longitude must be provided together",
        )

    bias = (latitude, longitude) if latitude is not None and longitude is not None else None
    try:
        provider_results = await provider.search_destinations(query, limit=limit, bias=bias)
    except GeographicProviderError as exc:
        if exc.status_code == 429:
            headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
            raise HTTPException(
                status_code=429,
                detail="Destination provider rate limit reached",
                headers=headers,
            ) from exc
        raise HTTPException(
            status_code=503 if exc.status_code == 503 else 502,
            detail="Destination search provider is unavailable",
        ) from exc

    return DestinationSearchResponse(results=[
        DestinationResponse(
            id=uuid5(NAMESPACE_URL, f"smartpark:google:{place.place_id}"),
            name=place.name,
            category=place.types[0] if place.types else None,
            address=place.address,
            location=CoordinateResponse(
                latitude=place.latitude,
                longitude=place.longitude,
            ),
        )
        for place in provider_results
    ])


@router.get("/{destination_id}", response_model=DestinationResponse)
def get_destination(
    destination_id: UUID,
    db: Session = Depends(get_db),
) -> DestinationResponse:
    location_geometry = cast(
        Destination.location,
        Geometry(geometry_type="POINT", srid=4326),
    )
    statement = (
        select(
            Destination,
            func.ST_Y(location_geometry),
            func.ST_X(location_geometry),
        )
        .where(Destination.id == destination_id)
    )
    row = db.execute(statement).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Destination not found")

    destination, latitude, longitude = row
    return DestinationResponse(
        id=destination.id,
        name=destination.name,
        category=destination.category,
        address=destination.address,
        location=CoordinateResponse(latitude=latitude, longitude=longitude),
    )
