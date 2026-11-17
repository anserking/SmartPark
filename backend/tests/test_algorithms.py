from decimal import Decimal

import pytest

from app.algorithms.dijkstra import dijkstra_tree
from app.algorithms.graph import RoadEdgeRecord, WeightedGraph, build_weighted_graph
from app.algorithms.ranking import (
    ParkingCandidate,
    rank_parking_candidates,
    sort_parking_by_fee,
)
from app.algorithms.sorting import merge_sort
from app.algorithms.trie import Trie


def test_trie_search_is_case_insensitive_and_returns_suggestions() -> None:
    trie = Trie()
    trie.insert("Bahria University Karachi")
    trie.insert("Bahria Town")
    trie.insert("Empress Market")
    trie.insert("BAHRIA UNIVERSITY KARACHI")

    assert trie.size == 3
    assert trie.prefix_search("  bAhRiA  ") == [
        "Bahria Town",
        "Bahria University Karachi",
    ]
    assert trie.prefix_search("unknown") == []


def test_dijkstra_finds_shortest_path_and_handles_unreachable_node() -> None:
    graph = WeightedGraph()
    graph.add_edge(1, 2, 4)
    graph.add_edge(1, 3, 1)
    graph.add_edge(3, 2, 1)
    graph.add_edge(2, 4, 1)
    graph.add_node(5)

    result = dijkstra_tree(graph, 1)

    assert result.distance_to(4) == 3
    assert result.path_to(4) == (1, 3, 2, 4)
    assert result.distance_to(5) is None
    assert result.path_to(5) is None


def test_graph_builder_respects_one_way_and_access_for_modes() -> None:
    edges = [
        RoadEdgeRecord(1, 2, 5, one_way=True),
        RoadEdgeRecord(2, 3, 7, access_type="private"),
    ]
    car_graph = build_weighted_graph([1, 2, 3], edges, "car")
    walking_graph = build_weighted_graph([1, 2, 3], edges, "walk")

    assert dijkstra_tree(car_graph, 1).distance_to(2) == 5
    assert dijkstra_tree(car_graph, 2).distance_to(1) is None
    assert dijkstra_tree(walking_graph, 2).distance_to(1) == 5
    assert dijkstra_tree(car_graph, 2).distance_to(3) is None


def test_parking_ranking_filters_known_incompatibility_and_unreachable() -> None:
    graph = WeightedGraph()
    graph.add_edge(1, 2, 200, bidirectional=True)
    graph.add_edge(2, 3, 100, bidirectional=True)
    graph.add_node(4)
    candidates = [
        ParkingCandidate("far", 3, supports_car=True),
        ParkingCandidate("near", 2, supports_car=None),
        ParkingCandidate("incompatible", 2, supports_car=False),
        ParkingCandidate("unreachable", 4, supports_car=True),
    ]

    ranked = rank_parking_candidates(graph, 1, candidates, "car")

    assert [(item.candidate.parking_id, item.road_distance_meters) for item in ranked] == [
        ("near", 200),
        ("far", 300),
    ]
    assert ranked[1].path == (1, 2, 3)


def test_merge_sort_is_stable_and_trie_rejects_invalid_limits() -> None:
    values = [("a", 2), ("b", 1), ("c", 2)]

    assert merge_sort(values, key=lambda value: value[1]) == [
        ("b", 1),
        ("a", 2),
        ("c", 2),
    ]
    with pytest.raises(ValueError):
        Trie().prefix_search("a", limit=0)


def test_custom_merge_sort_orders_known_fees_before_unknown() -> None:
    candidates = [
        ParkingCandidate("unknown", 1),
        ParkingCandidate("expensive", 1, hourly_fee=Decimal("50")),
        ParkingCandidate("free", 1, hourly_fee=Decimal("0")),
    ]

    ordered = sort_parking_by_fee(candidates)

    assert [candidate.parking_id for candidate in ordered] == [
        "free",
        "expensive",
        "unknown",
    ]
