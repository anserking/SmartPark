import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.algorithms.graph import RoadEdgeRecord, TravelMode, WeightedGraph, build_weighted_graph
from app.algorithms.ranking import ParkingCandidate, rank_parking_candidates
from app.services.geography import validate_coordinate

MAX_SNAP_DISTANCE_METERS = 500


@dataclass(frozen=True, slots=True)
class ParkingRecommendationCandidate:
    id: str
    latitude: float
    longitude: float
    supports_car: bool | None
    supports_bike: bool | None
    hourly_fee: Decimal | None


@dataclass(frozen=True, slots=True)
class RankedRecommendation:
    candidate: ParkingRecommendationCandidate
    destination_distance_meters: float
    distance_method: Literal["road", "straight_line"]


def _distance_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    earth_radius_meters = 6_371_000
    latitude_a_radians = math.radians(latitude_a)
    latitude_delta = math.radians(latitude_b - latitude_a)
    longitude_delta = math.radians(longitude_b - longitude_a)
    haversine = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(latitude_a_radians)
        * math.cos(math.radians(latitude_b))
        * math.sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_meters * math.asin(min(1, math.sqrt(haversine)))


def _nearest_node_id(
    latitude: float,
    longitude: float,
    node_locations: dict[int, tuple[float, float]],
) -> int | None:
    nearest_node: int | None = None
    nearest_distance = MAX_SNAP_DISTANCE_METERS
    for node_id, (node_latitude, node_longitude) in node_locations.items():
        distance = _distance_meters(
            latitude,
            longitude,
            node_latitude,
            node_longitude,
        )
        if distance < nearest_distance:
            nearest_node = node_id
            nearest_distance = distance
    return nearest_node


def _straight_line_rank(
    destination_latitude: float,
    destination_longitude: float,
    candidates: list[ParkingRecommendationCandidate],
    vehicle_type: Literal["car", "bike"],
    max_results: int,
) -> list[RankedRecommendation]:
    compatible = [
        candidate
        for candidate in candidates
        if (
            candidate.supports_car if vehicle_type == "car" else candidate.supports_bike
        )
        is not False
    ]
    compatible.sort(
        key=lambda candidate: (
            _distance_meters(
                destination_latitude,
                destination_longitude,
                candidate.latitude,
                candidate.longitude,
            ),
            candidate.id,
        )
    )
    return [
        RankedRecommendation(
            candidate=candidate,
            destination_distance_meters=_distance_meters(
                destination_latitude,
                destination_longitude,
                candidate.latitude,
                candidate.longitude,
            ),
            distance_method="straight_line",
        )
        for candidate in compatible[:max_results]
    ]


def rank_parking_recommendations(
    destination_latitude: float,
    destination_longitude: float,
    candidates: list[ParkingRecommendationCandidate],
    vehicle_type: Literal["car", "bike"],
    node_locations: dict[int, tuple[float, float]],
    edges: list[RoadEdgeRecord],
    max_results: int = 5,
) -> list[RankedRecommendation]:
    if max_results <= 0:
        raise ValueError("Maximum result count must be positive")
    validate_coordinate(destination_longitude, destination_latitude)

    compatible = [
        candidate
        for candidate in candidates
        if (
            candidate.supports_car if vehicle_type == "car" else candidate.supports_bike
        )
        is not False
    ]
    if not compatible or not node_locations or not edges:
        return _straight_line_rank(
            destination_latitude,
            destination_longitude,
            compatible,
            vehicle_type,
            max_results,
        )

    source_node = _nearest_node_id(
        destination_latitude,
        destination_longitude,
        node_locations,
    )
    if source_node is None:
        return _straight_line_rank(
            destination_latitude,
            destination_longitude,
            compatible,
            vehicle_type,
            max_results,
        )

    candidate_nodes = {
        candidate.id: _nearest_node_id(
            candidate.latitude,
            candidate.longitude,
            node_locations,
        )
        for candidate in compatible
    }
    if any(node_id is None for node_id in candidate_nodes.values()):
        return _straight_line_rank(
            destination_latitude,
            destination_longitude,
            compatible,
            vehicle_type,
            max_results,
        )

    mode: TravelMode = vehicle_type
    graph: WeightedGraph = build_weighted_graph(
        list(node_locations),
        edges,
        mode,
    )
    road_candidates: list[ParkingCandidate] = []
    for candidate in compatible:
        candidate_node = candidate_nodes[candidate.id]
        if candidate_node is None:
            return _straight_line_rank(
                destination_latitude,
                destination_longitude,
                compatible,
                vehicle_type,
                max_results,
            )
        road_candidates.append(
            ParkingCandidate(
                parking_id=candidate.id,
                node_id=candidate_node,
                supports_car=candidate.supports_car,
                supports_bike=candidate.supports_bike,
                hourly_fee=candidate.hourly_fee,
            )
        )
    ranked = rank_parking_candidates(
        graph,
        source_node,
        road_candidates,
        vehicle_type,
        max_results,
    )
    if not ranked:
        return _straight_line_rank(
            destination_latitude,
            destination_longitude,
            compatible,
            vehicle_type,
            max_results,
        )

    by_id = {candidate.id: candidate for candidate in compatible}
    return [
        RankedRecommendation(
            candidate=by_id[result.candidate.parking_id],
            destination_distance_meters=result.road_distance_meters,
            distance_method="road",
        )
        for result in ranked
    ]
