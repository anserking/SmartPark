from app.services.geography import geometry_from_osm
from app.services.parking_normalization import normalize_parking_elements


def test_normalizes_osm_node_and_deduplicates_by_type_and_id() -> None:
    node = {
        "type": "node",
        "id": 101,
        "lat": 24.86,
        "lon": 67.01,
        "tags": {"amenity": "parking", "name": "Example parking"},
    }

    results = normalize_parking_elements([node, node])

    assert len(results) == 1
    assert results[0].osm_id == "node/101"
    assert results[0].geometry == {
        "type": "Point",
        "coordinates": [67.01, 24.86],
    }


def test_preserves_closed_way_as_polygon_geometry() -> None:
    way = {
        "type": "way",
        "id": 202,
        "tags": {"amenity": "parking"},
        "geometry": [
            {"lat": 24.0, "lon": 67.0},
            {"lat": 24.0, "lon": 67.1},
            {"lat": 24.1, "lon": 67.1},
            {"lat": 24.0, "lon": 67.0},
        ],
    }

    geometry = geometry_from_osm(way)

    assert geometry["type"] == "Polygon"
    assert geometry["coordinates"][0][0] == geometry["coordinates"][0][-1]


def test_stitches_relation_members_and_preserves_inner_area() -> None:
    outer = [
        [[67.0, 24.0], [67.1, 24.0]],
        [[67.1, 24.0], [67.1, 24.1]],
        [[67.1, 24.1], [67.0, 24.1]],
        [[67.0, 24.1], [67.0, 24.0]],
    ]
    inner = [
        [[67.02, 24.02], [67.04, 24.02]],
        [[67.04, 24.02], [67.04, 24.04]],
        [[67.04, 24.04], [67.02, 24.04]],
        [[67.02, 24.04], [67.02, 24.02]],
    ]
    relation = {
        "type": "relation",
        "id": 303,
        "center": {"lat": 24.05, "lon": 67.05},
        "members": [
            {
                "type": "way",
                "role": role,
                "geometry": [{"lon": lon, "lat": lat} for lon, lat in segment],
            }
            for role, segments in (("outer", outer), ("inner", inner))
            for segment in segments
        ],
    }

    geometry = geometry_from_osm(relation)

    assert geometry["type"] == "Polygon"
    assert len(geometry["coordinates"]) == 2
    assert geometry["coordinates"][0][0] == geometry["coordinates"][0][-1]
    assert geometry["coordinates"][1][0] == geometry["coordinates"][1][-1]
