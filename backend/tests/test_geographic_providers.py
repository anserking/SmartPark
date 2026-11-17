import asyncio
from urllib.parse import parse_qs

import httpx
import pytest

from app.services.cache import TTLCache
from app.services.geocoding import PhotonGeocoder
from app.services.overpass import OverpassClient
from app.services.providers import GeographicProviderError


def test_photon_results_are_normalized_and_cached() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {"type": "Point", "coordinates": [67.03, 24.86]},
                        "properties": {
                            "name": "Bahria University",
                            "city": "Karachi",
                            "osm_type": "W",
                            "osm_id": 456,
                            "type": "college",
                        },
                    }
                ]
            },
        )

    async def run() -> tuple[object, object]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            geocoder = PhotonGeocoder(client=client, cache=TTLCache(60))
            first = await geocoder.search("Bahria University", bias=(24.86, 67.03))
            second = await geocoder.search(
                "  bahria   university  ", bias=(24.86, 67.03)
            )
        return first, second

    first, second = asyncio.run(run())

    assert first == second
    assert len(first) == 1
    assert first[0].osm_id == "W/456"
    assert first[0].address == "Karachi"
    assert len(requests) == 1


def test_overpass_queries_nodes_ways_relations_and_deduplicates() -> None:
    requests: list[httpx.Request] = []
    node = {
        "type": "node",
        "id": 101,
        "lat": 24.86,
        "lon": 67.01,
        "tags": {"amenity": "parking", "name": "Lot"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"elements": [node, node]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            overpass = OverpassClient(client=client, cache=TTLCache(60))
            return await overpass.nearby_parking(24.86, 67.01)

    results = asyncio.run(run())
    query = parse_qs(requests[0].content.decode("utf-8"))["data"][0]

    assert len(results) == 1
    assert results[0].osm_id == "node/101"
    assert all(f"{element_type}[" in query for element_type in ("node", "way", "relation"))
    assert "out center geom;" in query


def test_overpass_rate_limit_is_exposed_to_the_caller() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "30"})

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            overpass = OverpassClient(client=client, cache=TTLCache(60))
            await overpass.nearby_parking(24.86, 67.01)

    with pytest.raises(GeographicProviderError) as error:
        asyncio.run(run())

    assert error.value.provider == "Overpass"
    assert error.value.status_code == 429
    assert error.value.retry_after == "30"
