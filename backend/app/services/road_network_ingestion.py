from dataclasses import dataclass

from geoalchemy2 import WKTElement
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.algorithms.graph import RoadEdgeRecord
from app.models.road_network import RoadEdge, RoadNode
from app.services.google_places import GooglePlacesClient
from app.services.overpass import OverpassClient, overpass_client
from app.services.providers import GeographicProviderError
from app.services.road_network_normalization import (
    NormalizedRoadNetwork,
    RoadNodeCoordinate,
)


@dataclass(frozen=True, slots=True)
class RoadNetworkArea:
    name: str
    search_query: str
    radius_meters: int


KARACHI_ROAD_NETWORK_AREAS = (
    RoadNetworkArea(
        name="Bahria University Karachi",
        search_query="Bahria University Karachi",
        radius_meters=2000,
    ),
    RoadNetworkArea(
        name="Saddar",
        search_query="Saddar, Karachi",
        radius_meters=2000,
    ),
    RoadNetworkArea(
        name="Clifton",
        search_query="Clifton, Karachi",
        radius_meters=2000,
    ),
)


def _edge_identity(edge: RoadEdgeRecord) -> tuple[object, ...]:
    return (
        edge.source,
        edge.target,
        edge.distance_meters,
        edge.road_type,
        edge.access_type,
        edge.one_way,
        edge.car_access,
        edge.bike_access,
        edge.foot_access,
        edge.bike_one_way,
    )


async def fetch_karachi_road_network(
    provider: OverpassClient = overpass_client,
    locator: GooglePlacesClient | None = None,
) -> NormalizedRoadNetwork:
    nodes: dict[int, RoadNodeCoordinate] = {}
    edges: dict[tuple[object, ...], RoadEdgeRecord] = {}

    locator = locator or GooglePlacesClient()
    for area in KARACHI_ROAD_NETWORK_AREAS:
        candidates = await locator.search_destinations(area.search_query, limit=1)
        if not candidates:
            raise GeographicProviderError(
                "Google Places", f"no geocoding result for {area.name}"
            )
        center = candidates[0]
        region = await provider.roads_within(
            center.latitude,
            center.longitude,
            radius_meters=area.radius_meters,
        )
        if not region.edges:
            raise GeographicProviderError(
                "Overpass", f"no routable roads found for {area.name}"
            )
        nodes.update((node.osm_id, node) for node in region.nodes)
        edges.update((_edge_identity(edge), edge) for edge in region.edges)

    if not nodes or not edges:
        raise GeographicProviderError("Overpass", "no Karachi road data was found")

    return NormalizedRoadNetwork(
        nodes=tuple(nodes[node_id] for node_id in sorted(nodes)),
        edges=tuple(edges.values()),
    )


def replace_road_network(db: Session, network: NormalizedRoadNetwork) -> None:
    if not network.nodes or not network.edges:
        raise ValueError("Cannot replace the road network with empty data")

    db.execute(delete(RoadEdge))
    db.execute(delete(RoadNode))
    db.add_all(
        [
            RoadNode(
                id=node.osm_id,
                location=WKTElement(
                    f"POINT({node.longitude} {node.latitude})",
                    srid=4326,
                ),
                metadata_json={"source": "OpenStreetMap"},
            )
            for node in network.nodes
        ]
    )
    db.flush()
    db.add_all(
        [
            RoadEdge(
                source_node=edge.source,
                target_node=edge.target,
                distance_meters=edge.distance_meters,
                road_type=edge.road_type,
                access_type=edge.access_type,
                one_way=edge.one_way,
                car_access=edge.car_access,
                bike_access=edge.bike_access,
                foot_access=edge.foot_access,
                bike_one_way=edge.bike_one_way,
            )
            for edge in network.edges
        ]
    )
    db.commit()
