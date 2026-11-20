from app.algorithms.graph import RoadEdgeRecord
from app.services.parking_recommendations import (
    ParkingRecommendationCandidate,
    rank_parking_recommendations,
)


def _candidates() -> list[ParkingRecommendationCandidate]:
    return [
        ParkingRecommendationCandidate(
            id="parking-near",
            latitude=0,
            longitude=0.001,
            supports_car=True,
            supports_bike=True,
            hourly_fee=None,
        ),
        ParkingRecommendationCandidate(
            id="parking-fast",
            latitude=0,
            longitude=0.002,
            supports_car=True,
            supports_bike=True,
            hourly_fee=None,
        ),
        ParkingRecommendationCandidate(
            id="bike-only",
            latitude=0,
            longitude=0.003,
            supports_car=False,
            supports_bike=True,
            hourly_fee=None,
        ),
    ]


def test_recommendations_use_directed_road_distance_and_vehicle_filtering() -> None:
    node_locations = {
        1: (0, 0),
        2: (0, 0.001),
        3: (0, 0.002),
        4: (0, 0.003),
    }
    edges = [
        RoadEdgeRecord(source=1, target=2, distance_meters=500, one_way=True),
        RoadEdgeRecord(source=1, target=3, distance_meters=200, one_way=True),
        RoadEdgeRecord(source=1, target=4, distance_meters=50, one_way=True),
    ]

    recommendations = rank_parking_recommendations(
        destination_latitude=0,
        destination_longitude=0,
        candidates=_candidates(),
        vehicle_type="car",
        node_locations=node_locations,
        edges=edges,
    )

    assert [item.candidate.id for item in recommendations] == [
        "parking-fast",
        "parking-near",
    ]
    assert [item.destination_distance_meters for item in recommendations] == [
        200,
        500,
    ]
    assert {item.distance_method for item in recommendations} == {"road"}


def test_recommendations_explicitly_fall_back_to_straight_line_without_graph() -> None:
    recommendations = rank_parking_recommendations(
        destination_latitude=0,
        destination_longitude=0,
        candidates=_candidates(),
        vehicle_type="car",
        node_locations={},
        edges=[],
        max_results=1,
    )

    assert len(recommendations) == 1
    assert recommendations[0].candidate.id == "parking-near"
    assert recommendations[0].distance_method == "straight_line"


def test_recommendations_fall_back_when_a_facility_cannot_be_snapped() -> None:
    candidates = _candidates()[:2]
    candidates[1] = ParkingRecommendationCandidate(
        id=candidates[1].id,
        latitude=0,
        longitude=0.01,
        supports_car=True,
        supports_bike=True,
        hourly_fee=None,
    )
    recommendations = rank_parking_recommendations(
        destination_latitude=0,
        destination_longitude=0,
        candidates=candidates,
        vehicle_type="car",
        node_locations={1: (0, 0), 2: (0, 0.001)},
        edges=[RoadEdgeRecord(source=1, target=2, distance_meters=100)],
    )

    assert recommendations[0].distance_method == "straight_line"
