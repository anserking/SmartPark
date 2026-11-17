import heapq
from dataclasses import dataclass
from decimal import Decimal
from itertools import count
from typing import Literal, Sequence

from app.algorithms.dijkstra import dijkstra_tree
from app.algorithms.graph import WeightedGraph
from app.algorithms.sorting import merge_sort

VehicleType = Literal["car", "bike"]


@dataclass(frozen=True, slots=True)
class ParkingCandidate:
    parking_id: str
    node_id: int
    supports_car: bool | None = None
    supports_bike: bool | None = None
    hourly_fee: Decimal | None = None


@dataclass(frozen=True, slots=True)
class RankedParking:
    candidate: ParkingCandidate
    road_distance_meters: float
    path: tuple[int, ...]


def rank_parking_candidates(
    graph: WeightedGraph,
    source_node: int,
    candidates: list[ParkingCandidate],
    vehicle_type: VehicleType,
    max_results: int = 5,
) -> list[RankedParking]:
    if max_results <= 0:
        raise ValueError("Maximum result count must be positive")

    shortest_paths = dijkstra_tree(graph, source_node)
    pending: list[tuple[float, str, int, ParkingCandidate, tuple[int, ...]]] = []
    sequence = count()

    for candidate in candidates:
        compatible = (
            candidate.supports_car if vehicle_type == "car" else candidate.supports_bike
        )
        if compatible is False:
            continue

        distance = shortest_paths.distance_to(candidate.node_id)
        path = shortest_paths.path_to(candidate.node_id)
        if distance is None or path is None:
            continue
        heapq.heappush(
            pending,
            (distance, candidate.parking_id, next(sequence), candidate, path),
        )

    ranked: list[RankedParking] = []
    while pending and len(ranked) < max_results:
        distance, _, _, candidate, path = heapq.heappop(pending)
        ranked.append(RankedParking(candidate, distance, path))
    return ranked


def sort_parking_by_fee(
    candidates: Sequence[ParkingCandidate],
) -> list[ParkingCandidate]:
    return merge_sort(
        candidates,
        key=lambda candidate: (
            candidate.hourly_fee is None,
            candidate.hourly_fee if candidate.hourly_fee is not None else Decimal("0"),
            candidate.parking_id,
        ),
    )
