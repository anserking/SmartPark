from typing import Literal

from pydantic import BaseModel, Field


class RouteCoordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: RouteCoordinate
    destination: RouteCoordinate


class RouteGeometry(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[tuple[float, float]] = Field(min_length=2)


class RouteResponse(BaseModel):
    geometry: RouteGeometry
    distance_meters: float = Field(ge=0, serialization_alias="distanceMeters")
    duration_seconds: float = Field(ge=0, serialization_alias="durationSeconds")
