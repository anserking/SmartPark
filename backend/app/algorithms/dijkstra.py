import heapq
from dataclasses import dataclass
from typing import Mapping

from app.algorithms.graph import WeightedGraph


@dataclass(frozen=True, slots=True)
class ShortestPathTree:
    source: int
    distances: Mapping[int, float]
    predecessors: Mapping[int, int]

    def distance_to(self, destination: int) -> float | None:
        return self.distances.get(destination)

    def path_to(self, destination: int) -> tuple[int, ...] | None:
        if destination not in self.distances:
            return None

        path = [destination]
        while path[-1] != self.source:
            predecessor = self.predecessors.get(path[-1])
            if predecessor is None:
                return None
            path.append(predecessor)
        path.reverse()
        return tuple(path)


def dijkstra_tree(graph: WeightedGraph, source: int) -> ShortestPathTree:
    if not graph.contains(source):
        raise ValueError(f"Source node {source} is not in the graph")

    distances = {source: 0.0}
    predecessors: dict[int, int] = {}
    pending: list[tuple[float, int]] = [(0.0, source)]

    while pending:
        current_distance, current_node = heapq.heappop(pending)
        if current_distance != distances.get(current_node):
            continue

        for edge in graph.neighbors(current_node):
            candidate_distance = current_distance + edge.distance_meters
            known_distance = distances.get(edge.target)
            if known_distance is not None and candidate_distance >= known_distance:
                continue
            distances[edge.target] = candidate_distance
            predecessors[edge.target] = current_node
            heapq.heappush(pending, (candidate_distance, edge.target))

    return ShortestPathTree(source, distances, predecessors)
