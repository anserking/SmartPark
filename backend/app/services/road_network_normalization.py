import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.algorithms.graph import RoadEdgeRecord
from app.services.geography import validate_coordinate

EARTH_RADIUS_METERS = 6_371_008.8
DENIED_ACCESS_VALUES = {"no", "private", "restricted"}
NON_ROUTABLE_HIGHWAYS = {
    "abandoned",
    "construction",
    "proposed",
    "razed",
}
CAR_RESTRICTED_HIGHWAYS = {
    "bridleway",
    "cycleway",
    "footway",
    "path",
    "pedestrian",
    "steps",
}
BIKE_RESTRICTED_HIGHWAYS = {
    "bridleway",
    "footway",
    "pedestrian",
    "steps",
}
FOOT_RESTRICTED_HIGHWAYS = {"motorway", "motorway_link"}


@dataclass(frozen=True, slots=True)
class RoadNodeCoordinate:
    osm_id: int
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class NormalizedRoadNetwork:
    nodes: tuple[RoadNodeCoordinate, ...]
    edges: tuple[RoadEdgeRecord, ...]


def _distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    latitude_delta = math.radians(latitude_b - latitude_a)
    longitude_delta = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(math.radians(latitude_a))
        * math.cos(math.radians(latitude_b))
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(haversine))


def _access_for_mode(tags: Mapping[str, str], mode: str, highway: str) -> str:
    access_keys = {
        "car": ("motorcar", "motor_vehicle", "vehicle", "access"),
        "bike": ("bicycle", "vehicle", "access"),
        "walk": ("foot", "access"),
    }
    for key in access_keys[mode]:
        value = tags.get(key)
        if value is not None:
            return value.strip().lower()

    restricted_highways = {
        "car": CAR_RESTRICTED_HIGHWAYS,
        "bike": BIKE_RESTRICTED_HIGHWAYS,
        "walk": FOOT_RESTRICTED_HIGHWAYS,
    }
    if highway in restricted_highways[mode]:
        return "no"
    return "yes"


def _one_way_for_mode(tags: Mapping[str, str], mode: str) -> tuple[bool, bool]:
    keys = {
        "car": ("oneway:motorcar", "oneway:motor_vehicle", "oneway"),
        "bike": ("oneway:bicycle", "oneway"),
        "walk": ("oneway:foot",),
    }
    value = next((tags[key] for key in keys[mode] if key in tags), None)
    if value is None:
        if mode != "walk" and tags.get("junction", "").lower() == "roundabout":
            value = "yes"
        else:
            return False, False

    normalized = value.strip().lower()
    if normalized in {"no", "0", "false"}:
        return False, False
    if normalized == "-1":
        return True, True
    return normalized in {"yes", "1", "true"}, False


def _valid_osm_id(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def normalize_road_network_elements(
    elements: Sequence[object],
    center_latitude: float,
    center_longitude: float,
    radius_meters: int,
) -> NormalizedRoadNetwork:
    if not 100 <= radius_meters <= 5000:
        raise ValueError("Road network radius must be between 100 and 5000 meters")
    validate_coordinate(center_longitude, center_latitude)

    nodes_by_id: dict[int, RoadNodeCoordinate] = {}
    ways: list[tuple[Mapping[str, object], Mapping[str, str], list[int]]] = []

    for element in elements:
        if not isinstance(element, Mapping):
            continue

        element_type = element.get("type")
        osm_id = _valid_osm_id(element.get("id"))
        if osm_id is None:
            continue

        if element_type == "node":
            try:
                longitude, latitude = validate_coordinate(
                    element.get("lon"), element.get("lat")
                )
            except ValueError:
                continue
            if (
                _distance_meters(
                    center_latitude,
                    center_longitude,
                    latitude,
                    longitude,
                )
                <= radius_meters
            ):
                nodes_by_id[osm_id] = RoadNodeCoordinate(
                    osm_id=osm_id,
                    latitude=latitude,
                    longitude=longitude,
                )
            continue

        if element_type != "way":
            continue
        raw_tags = element.get("tags")
        raw_nodes = element.get("nodes")
        if not isinstance(raw_tags, Mapping) or not isinstance(raw_nodes, Sequence):
            continue
        raw_highway = raw_tags.get("highway")
        if not isinstance(raw_highway, str):
            continue
        tags = {
            key: value.strip()
            for key, value in raw_tags.items()
            if isinstance(key, str) and isinstance(value, str)
        }
        highway = tags.get("highway", "").lower()
        if not highway or highway in NON_ROUTABLE_HIGHWAYS:
            continue
        node_ids = [
            node_id
            for value in raw_nodes
            if (node_id := _valid_osm_id(value)) is not None
        ]
        if len(node_ids) >= 2 and tags.get("area", "").lower() != "yes":
            raw_geometry = element.get("geometry")
            if isinstance(raw_geometry, Sequence) and len(raw_geometry) == len(node_ids):
                for node_id, point in zip(node_ids, raw_geometry):
                    if not isinstance(point, Mapping):
                        continue
                    try:
                        longitude, latitude = validate_coordinate(
                            point.get("lon"), point.get("lat")
                        )
                    except ValueError:
                        continue
                    if (
                        _distance_meters(
                            center_latitude,
                            center_longitude,
                            latitude,
                            longitude,
                        )
                        <= radius_meters
                    ):
                        nodes_by_id[node_id] = RoadNodeCoordinate(
                            osm_id=node_id,
                            latitude=latitude,
                            longitude=longitude,
                        )
            ways.append((element, tags, node_ids))

    edge_records: dict[tuple[object, ...], RoadEdgeRecord] = {}
    used_node_ids: set[int] = set()

    for _way, tags, way_node_ids in ways:
        highway = tags["highway"].lower()
        if highway in NON_ROUTABLE_HIGHWAYS:
            continue

        mode_access = {
            mode: _access_for_mode(tags, mode, highway)
            for mode in ("car", "bike", "walk")
        }
        one_way_modes = {
            mode: _one_way_for_mode(tags, mode)
            for mode in ("car", "bike", "walk")
        }
        for mode, access in mode_access.items():
            if access in DENIED_ACCESS_VALUES:
                continue

            one_way, reverse = one_way_modes[mode]
            ordered_nodes = list(reversed(way_node_ids)) if reverse else way_node_ids
            for source_id, target_id in zip(ordered_nodes, ordered_nodes[1:]):
                source = nodes_by_id.get(source_id)
                target = nodes_by_id.get(target_id)
                if source is None or target is None:
                    continue
                distance = _distance_meters(
                    source.latitude,
                    source.longitude,
                    target.latitude,
                    target.longitude,
                )
                if distance <= 0:
                    continue

                edge = RoadEdgeRecord(
                    source=source_id,
                    target=target_id,
                    distance_meters=distance,
                    road_type=highway,
                    access_type=tags.get("access"),
                    one_way=one_way if mode == "car" else False,
                    car_access=mode_access["car"] if mode == "car" else "no",
                    bike_access=mode_access["bike"] if mode == "bike" else "no",
                    foot_access=mode_access["walk"] if mode == "walk" else "no",
                    bike_one_way=one_way if mode == "bike" else None,
                )
                identity = (
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
                edge_records.setdefault(identity, edge)
                used_node_ids.update((source_id, target_id))

    nodes = tuple(
        nodes_by_id[node_id]
        for node_id in sorted(used_node_ids)
    )
    edges = tuple(edge_records.values())
    return NormalizedRoadNetwork(nodes=nodes, edges=edges)
