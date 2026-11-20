import hmac
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from geoalchemy2 import WKTElement
from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.parking_spot import ParkingSpot
from app.schemas.admin import (
    AdminParkingSpotResponse,
    ParkingSpotUpdate,
    ParkingSpotWrite,
)
from app.schemas.destination import CoordinateResponse

router = APIRouter(prefix="/api/admin/parking", tags=["admin"])


def require_admin_key(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    expected_key = settings.admin_api_key
    if expected_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Parking administration is not configured",
        )

    scheme, separator, supplied_key = (authorization or "").partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not hmac.compare_digest(
            supplied_key, expected_key.get_secret_value()
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid admin key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _response(spot: ParkingSpot) -> AdminParkingSpotResponse:
    point = to_shape(spot.location)
    if point.geom_type != "Point":
        point = point.representative_point()

    return AdminParkingSpotResponse(
        id=spot.id,
        name=spot.name,
        address=spot.address,
        location=CoordinateResponse(latitude=point.y, longitude=point.x),
        parking_type=spot.parking_type,
        hourly_fee=spot.hourly_fee,
        supports_car=spot.supports_car,
        supports_bike=spot.supports_bike,
        capacity=spot.capacity,
        available_spaces=spot.available_spaces,
        availability_status=spot.availability_status,
        verification_status=spot.verification_status,
        source=spot.source,
    )


def _location(value: CoordinateResponse) -> WKTElement:
    return WKTElement(
        f"POINT({value.longitude} {value.latitude})",
        srid=4326,
    )


@router.get(
    "",
    response_model=list[AdminParkingSpotResponse],
    dependencies=[Depends(require_admin_key)],
)
def list_parking_spots(
    db: Session = Depends(get_db),
) -> list[AdminParkingSpotResponse]:
    spots = db.scalars(
        select(ParkingSpot).order_by(ParkingSpot.updated_at.desc(), ParkingSpot.id)
    ).all()
    return [_response(spot) for spot in spots]


@router.post(
    "",
    response_model=AdminParkingSpotResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_key)],
)
def create_parking_spot(
    payload: ParkingSpotWrite,
    db: Session = Depends(get_db),
) -> AdminParkingSpotResponse:
    values = payload.model_dump(exclude={"location"})
    spot = ParkingSpot(
        **values,
        location=_location(payload.location),
        source="admin",
    )
    if spot.verification_status == "verified":
        spot.last_verified_at = datetime.now(timezone.utc)
    db.add(spot)
    db.commit()
    db.refresh(spot)
    return _response(spot)


@router.patch(
    "/{spot_id}",
    response_model=AdminParkingSpotResponse,
    dependencies=[Depends(require_admin_key)],
)
def update_parking_spot(
    spot_id: UUID,
    payload: ParkingSpotUpdate,
    db: Session = Depends(get_db),
) -> AdminParkingSpotResponse:
    spot = db.get(ParkingSpot, spot_id)
    if spot is None:
        raise HTTPException(status_code=404, detail="Parking record not found")

    values = payload.model_dump(exclude_unset=True)
    location = values.pop("location", None)
    if location is not None:
        values["location"] = _location(location)

    for field, value in values.items():
        setattr(spot, field, value)
    if values.get("verification_status") == "verified":
        spot.last_verified_at = datetime.now(timezone.utc)
    elif values.get("verification_status") == "unverified":
        spot.last_verified_at = None

    db.commit()
    db.refresh(spot)
    return _response(spot)


@router.delete(
    "/{spot_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, bool],
    dependencies=[Depends(require_admin_key)],
)
def delete_parking_spot(
    spot_id: UUID,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    spot = db.get(ParkingSpot, spot_id)
    if spot is None:
        raise HTTPException(status_code=404, detail="Parking record not found")
    db.delete(spot)
    db.commit()
    return {"deleted": True}
