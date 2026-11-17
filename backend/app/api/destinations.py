from uuid import UUID, uuid5, NAMESPACE_URL

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2 import Geometry, WKTElement
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from app.algorithms.trie import Trie
from app.db.session import get_db
from app.models.destination import Destination
from app.schemas.destination import (
    CoordinateResponse,
    DestinationResponse,
    DestinationSearchResponse,
)
from app.services.geocoding import DestinationCandidate, PhotonGeocoder, geocoder
from app.services.providers import GeographicProviderError

router = APIRouter(prefix="/api/destinations", tags=["destinations"])


class DestinationSearchIndex:
    def __init__(self) -> None:
        self._trie = Trie()
        self._by_name: dict[str, dict[str, DestinationCandidate]] = {}

    def remember(self, candidate: DestinationCandidate) -> None:
        normalized_name = Trie.normalize(candidate.name)
        if not normalized_name:
            return
        self._trie.insert(candidate.name)
        key = candidate.osm_id or (
            f"{candidate.latitude:.6f},{candidate.longitude:.6f}"
        )
        self._by_name.setdefault(normalized_name, {})[key] = candidate

    def suggestions(self, prefix: str, limit: int) -> tuple[DestinationCandidate, ...]:
        names = self._trie.prefix_search(prefix, limit)
        return tuple(
            candidate
            for name in names
            for candidate in self._by_name.get(Trie.normalize(name), {}).values()
        )


destination_search_index = DestinationSearchIndex()


def get_geocoder() -> PhotonGeocoder:
    return geocoder


def get_search_index() -> DestinationSearchIndex:
    return destination_search_index


def _candidate_identity(candidate: DestinationCandidate) -> str:
    return candidate.osm_id or (
        f"{Trie.normalize(candidate.name)}:"
        f"{candidate.latitude:.6f}:{candidate.longitude:.6f}"
    )


def _destination_id(candidate: DestinationCandidate) -> UUID:
    identity = candidate.osm_id or (
        f"{Trie.normalize(candidate.name)}:"
        f"{candidate.latitude:.6f}:{candidate.longitude:.6f}"
    )
    return uuid5(NAMESPACE_URL, f"smartpark:destination:{identity}")


def _save_candidate(
    db: Session, candidate: DestinationCandidate
) -> DestinationResponse:
    destination_id = _destination_id(candidate)
    destination = db.get(Destination, destination_id)
    location = WKTElement(
        f"POINT({candidate.longitude} {candidate.latitude})",
        srid=4326,
    )
    if destination is None:
        destination = Destination(
            id=destination_id,
            name=candidate.name,
            category=candidate.category,
            address=candidate.address,
            location=location,
            osm_id=candidate.osm_id,
        )
        db.add(destination)
    else:
        destination.name = candidate.name
        destination.category = candidate.category
        destination.address = candidate.address
        destination.location = location

    return DestinationResponse(
        id=destination_id,
        name=candidate.name,
        category=candidate.category,
        address=candidate.address,
        location=CoordinateResponse(
            latitude=candidate.latitude,
            longitude=candidate.longitude,
        ),
    )


@router.get("/search", response_model=DestinationSearchResponse)
async def search_destinations(
    q: str = Query(min_length=2, max_length=150),
    limit: int = Query(default=5, ge=1, le=10),
    latitude: float | None = Query(default=None, ge=-90, le=90),
    longitude: float | None = Query(default=None, ge=-180, le=180),
    db: Session = Depends(get_db),
    provider: PhotonGeocoder = Depends(get_geocoder),
    search_index: DestinationSearchIndex = Depends(get_search_index),
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
        provider_results = await provider.search(query, limit=limit, bias=bias)
    except GeographicProviderError as exc:
        if exc.status_code == 429:
            headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
            raise HTTPException(
                status_code=429,
                detail="Destination provider rate limit reached",
                headers=headers,
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Destination search provider is unavailable",
        ) from exc

    for candidate in provider_results:
        search_index.remember(candidate)

    merged: dict[str, DestinationCandidate] = {}
    for candidate in (*provider_results, *search_index.suggestions(query, limit)):
        merged.setdefault(_candidate_identity(candidate), candidate)
        if len(merged) >= limit:
            break

    results = [_save_candidate(db, candidate) for candidate in merged.values()]
    db.commit()
    return DestinationSearchResponse(results=results)


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
