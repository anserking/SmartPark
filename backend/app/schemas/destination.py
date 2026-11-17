from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CoordinateResponse(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class DestinationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str | None
    address: str | None
    location: CoordinateResponse


class DestinationSearchResponse(BaseModel):
    results: list[DestinationResponse]
