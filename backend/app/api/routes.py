from typing import Literal

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.routing import RouteRequest, RouteResponse
from app.services.google_routes import GoogleRoutesClient, google_routes_client
from app.services.providers import GeographicProviderError
from app.services.routing import (
    RoutingConfigurationError,
)

router = APIRouter(prefix="/api/routes", tags=["routes"])


def get_routing_client() -> GoogleRoutesClient:
    return google_routes_client


@router.post("/{mode}", response_model=RouteResponse)
async def get_route(
    mode: Literal["car", "bike", "walk"],
    request: RouteRequest,
    provider: GoogleRoutesClient = Depends(get_routing_client),
) -> RouteResponse:
    try:
        return await provider.route(request.origin, request.destination, mode)
    except RoutingConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="Routing provider is not configured",
        ) from exc
    except GeographicProviderError as exc:
        if exc.status_code == 429:
            headers = {"Retry-After": exc.retry_after} if exc.retry_after else None
            raise HTTPException(
                status_code=429,
                detail="Routing provider rate limit reached",
                headers=headers,
            ) from exc
        raise HTTPException(
            status_code=502,
            detail="Routing provider is unavailable",
        ) from exc
