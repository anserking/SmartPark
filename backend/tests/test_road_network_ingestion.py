import asyncio
from urllib.parse import parse_qs

import httpx

from app.algorithms.dijkstra import dijkstra_tree
from app.algorithms.graph import build_weighted_graph
from app.services.cache import TTLCache
from app.services.geocoding import DestinationCandidate
from app.services.overpass import OverpassClient
from app.services.road_network_ingestion import (
    KARACHI_ROAD_NETWORK_AREAS,
    fetch_karachi_road_network,
    replace_road_network,
)
from app.services.road_network_normalization import (
    NormalizedRoadNetwork,
    normalize_road_network_elements,
)


def _elements() -> list[dict[str, object]]:
    return [
        {"type": "way", "id": 10, "nodes": [1, 2], "tags": {
            "highway": "residential",
            "oneway": "yes",
            "oneway:bicycle": "no",
        }},
        {"type": "way", "id": 11, "nodes": [2, 3], "tags": {
            "highway": "footway",
            "foot": "designated",
        }},
        {"type": "way", "id": 12, "nodes": [3, 4], "tags": {
            "highway": "residential",
        }},
        {"type": "node", "id": 1, "lat": 24.86, "lon": 67.01},
        {"type": "node", "id": 2, "lat": 24.86, "lon": 67.011},
        {"type": "node", "id": 3, "lat": 24.86, "lon": 67.012},
        {"type": "node", "id": 4, "lat": 24.86, "lon": 67.03},
    ]


def test_road_normalization_bounds_data_and_preserves_mode_access() -> None:
    network = normalize_road_network_elements(
        _elements(),
        center_latitude=24.86,
        center_longitude=67.01,
        radius_meters=500,
    )

    assert {node.osm_id for node in network.nodes} == {1, 2, 3}
    residential_car = next(
        edge
        for edge in network.edges
        if edge.road_type == "residential" and edge.car_access == "yes"
    )
    residential_bike = next(
        edge
        for edge in network.edges
        if edge.road_type == "residential" and edge.bike_access == "yes"
    )
    footway = next(edge for edge in network.edges if edge.road_type == "footway")

    assert (residential_car.source, residential_car.target) == (1, 2)
    assert residential_car.one_way is True
    assert residential_bike.bike_one_way is False
    assert footway.car_access == "no"
    assert footway.bike_access == "no"
    assert footway.foot_access == "designated"
    assert 0 < residential_car.distance_meters < 200

    car_graph = build_weighted_graph([1, 2, 3], list(network.edges), "car")
    walking_graph = build_weighted_graph([1, 2, 3], list(network.edges), "walk")
    assert dijkstra_tree(car_graph, 2).distance_to(1) is None
    assert dijkstra_tree(walking_graph, 3).distance_to(2) is not None


def test_road_normalization_reverses_reverse_oneway_and_ignores_closed_areas() -> None:
    elements = [
        {"type": "way", "id": 20, "nodes": [1, 2], "tags": {
            "highway": "primary",
            "oneway": "-1",
        }},
        {"type": "way", "id": 21, "nodes": [1, 2], "tags": {
            "highway": "residential",
            "area": "yes",
        }},
        {"type": "node", "id": 1, "lat": 24.86, "lon": 67.01},
        {"type": "node", "id": 2, "lat": 24.86, "lon": 67.011},
    ]

    network = normalize_road_network_elements(
        elements,
        center_latitude=24.86,
        center_longitude=67.01,
        radius_meters=500,
    )
    car_edge = next(edge for edge in network.edges if edge.car_access == "yes")

    assert len(network.edges) == 3
    assert (car_edge.source, car_edge.target) == (2, 1)
    assert car_edge.one_way is True


def test_ingestion_geocodes_all_regions_and_deduplicates_overlapping_roads() -> None:
    region = normalize_road_network_elements(
        _elements(),
        center_latitude=24.86,
        center_longitude=67.01,
        radius_meters=500,
    )
    location_queries: list[str] = []
    provider_calls: list[tuple[float, float, int]] = []
    candidate = DestinationCandidate(
        name="Karachi",
        category="place",
        address="Karachi",
        latitude=24.86,
        longitude=67.01,
        osm_id="N/1",
    )

    class StubLocator:
        async def search(self, query: str, limit: int = 1, bias=None):
            location_queries.append(query)
            return (candidate,)

    class StubOverpass:
        async def roads_within(
            self,
            latitude: float,
            longitude: float,
            radius_meters: int,
        ) -> NormalizedRoadNetwork:
            provider_calls.append((latitude, longitude, radius_meters))
            return region

    network = asyncio.run(
        fetch_karachi_road_network(
            provider=StubOverpass(),
            locator=StubLocator(),
        )
    )

    assert location_queries == [area.search_query for area in KARACHI_ROAD_NETWORK_AREAS]
    assert provider_calls == [
        (24.86, 67.01, area.radius_meters)
        for area in KARACHI_ROAD_NETWORK_AREAS
    ]
    assert network == region


def test_persistence_replaces_road_tables_in_foreign_key_order() -> None:
    network = normalize_road_network_elements(
        _elements(),
        center_latitude=24.86,
        center_longitude=67.01,
        radius_meters=500,
    )

    class StubSession:
        def __init__(self) -> None:
            self.deleted_tables: list[str] = []
            self.added_objects: list[object] = []
            self.commits = 0

        def execute(self, statement: object) -> None:
            self.deleted_tables.append(statement.table.name)

        def add_all(self, objects: list[object]) -> None:
            self.added_objects.extend(objects)

        def commit(self) -> None:
            self.commits += 1

    session = StubSession()
    replace_road_network(session, network)
    replace_road_network(session, network)

    assert session.deleted_tables == [
        "road_edges",
        "road_nodes",
        "road_edges",
        "road_nodes",
    ]
    assert session.commits == 2
    assert len(session.added_objects) == (len(network.nodes) + len(network.edges)) * 2


def test_overpass_road_query_is_bounded_and_cached() -> None:
    requests: list[httpx.Request] = []
    elements = _elements()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"elements": elements})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            overpass = OverpassClient(client=client, cache=TTLCache(60))
            first = await overpass.roads_within(24.86, 67.01, radius_meters=500)
            second = await overpass.roads_within(24.86, 67.01, radius_meters=500)
        return first, second

    first, second = asyncio.run(run())
    query = parse_qs(requests[0].content.decode("utf-8"))["data"][0]

    assert first == second
    assert len(requests) == 1
    assert "way(around:500,24.860000,67.010000)[\"highway\"];" in query
    assert "out body geom;" in query
    assert ">" not in query
