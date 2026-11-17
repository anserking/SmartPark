import math
from dataclasses import dataclass
from typing import Literal


TravelMode = Literal["car", "bike", "walk"]


@dataclass(frozen=True, slots=True)
class WeightedEdge:
    target: int
    distance_meters: float


@dataclass(frozen=True, slots=True)
class RoadEdgeRecord:
    source: int
    target: int
    distance_meters: float
    road_type: str | None = None
    access_type: str | None = None
    one_way: bool = False
    car_access: str | None = None
    bike_access: str | None = None
    foot_access: str | None = None
    bike_one_way: bool | None = None


class WeightedGraph:
    def __init__(self) -> None:
        self._adjacency: dict[int, list[WeightedEdge]] = {}

    def add_node(self, node_id: int) -> None:
        self._adjacency.setdefault(node_id, [])

    def add_edge(
        self,
        source: int,
        target: int,
        distance_meters: float,
        bidirectional: bool = False,
    ) -> None:
        if not math.isfinite(distance_meters) or distance_meters < 0:
            raise ValueError("Edge distance must be a finite non-negative number")

        self.add_node(source)
        self.add_node(target)
        self._adjacency[source].append(WeightedEdge(target, distance_meters))
        if bidirectional:
            self._adjacency[target].append(WeightedEdge(source, distance_meters))

    def contains(self, node_id: int) -> bool:
        return node_id in self._adjacency

    def neighbors(self, node_id: int) -> tuple[WeightedEdge, ...]:
        return tuple(self._adjacency.get(node_id, ()))

    @property
    def node_ids(self) -> tuple[int, ...]:
        return tuple(self._adjacency)


def build_weighted_graph(
    node_ids: list[int],
    edges: list[RoadEdgeRecord],
    mode: TravelMode,
) -> WeightedGraph:
    graph = WeightedGraph()
    for node_id in node_ids:
        graph.add_node(node_id)

    for edge in edges:
        mode_access = {
            "car": edge.car_access,
            "bike": edge.bike_access,
            "walk": edge.foot_access,
        }[mode]
        access = (mode_access or edge.access_type or "").strip().lower()
        if access in {"no", "private", "restricted"}:
            continue
        if (
            mode == "car"
            and mode_access is None
            and access in {"foot", "pedestrian", "bicycle"}
        ):
            continue
        if (
            mode in {"bike", "walk"}
            and mode_access is None
            and access in {"motor_vehicle", "motorcar"}
        ):
            continue

        one_way = edge.one_way
        if mode == "bike" and edge.bike_one_way is not None:
            one_way = edge.bike_one_way

        graph.add_edge(
            edge.source,
            edge.target,
            edge.distance_meters,
            bidirectional=not one_way or mode == "walk",
        )

    return graph
