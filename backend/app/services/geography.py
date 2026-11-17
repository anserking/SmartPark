from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict

logger = logging.getLogger(__name__)

GeometryType = Literal[
    "Point",
    "LineString",
    "Polygon",
    "MultiLineString",
    "MultiPolygon",
    "GeometryCollection",
]


class GeoJSONGeometry(TypedDict):
    type: GeometryType
    coordinates: object


class GeoJSONGeometryCollection(TypedDict):
    type: Literal["GeometryCollection"]
    geometries: list[GeoJSONGeometry | GeoJSONGeometryCollection]


def validate_coordinate(longitude: object, latitude: object) -> list[float]:
    if isinstance(longitude, bool) or isinstance(latitude, bool):
        raise ValueError("Coordinates must be numeric")
    if not isinstance(longitude, (int, float)) or not isinstance(latitude, (int, float)):
        raise ValueError("Coordinates must be numeric")
    lon = float(longitude)
    lat = float(latitude)
    if not math.isfinite(lon) or not math.isfinite(lat):
        raise ValueError("Coordinates must be finite")
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError("Coordinates are outside valid longitude/latitude bounds")
    return [lon, lat]


def _element_point(element: Mapping[str, object]) -> GeoJSONGeometry | None:
    latitude = element.get("lat")
    longitude = element.get("lon")
    if latitude is None or longitude is None:
        return None
    return {"type": "Point", "coordinates": validate_coordinate(longitude, latitude)}


def _coordinates_from_geometry(value: object) -> list[list[float]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("OSM geometry must be a coordinate sequence")

    coordinates: list[list[float]] = []
    for point in value:
        if not isinstance(point, Mapping):
            raise ValueError("OSM geometry contains an invalid point")
        coordinates.append(validate_coordinate(point.get("lon"), point.get("lat")))
    if not coordinates:
        raise ValueError("OSM geometry is empty")
    return coordinates


def _way_geometry(element: Mapping[str, object]) -> GeoJSONGeometry | None:
    raw_geometry = element.get("geometry")
    if raw_geometry is None:
        return None
    coordinates = _coordinates_from_geometry(raw_geometry)
    if len(coordinates) == 1:
        return {"type": "Point", "coordinates": coordinates[0]}
    if (
        len(coordinates) >= 4
        and coordinates[0] == coordinates[-1]
        and len({tuple(point) for point in coordinates[:-1]}) >= 3
    ):
        return {"type": "Polygon", "coordinates": [coordinates]}
    return {"type": "LineString", "coordinates": coordinates}


def _signed_area(ring: list[list[float]]) -> float:
    return sum(
        ring[index][0] * ring[index + 1][1]
        - ring[index + 1][0] * ring[index][1]
        for index in range(len(ring) - 1)
    ) / 2


def _orient_ring(ring: list[list[float]], counterclockwise: bool) -> list[list[float]]:
    is_counterclockwise = _signed_area(ring) > 0
    if is_counterclockwise == counterclockwise:
        return ring
    return list(reversed(ring))


def _stitch_rings(
    segments: list[list[list[float]]],
) -> tuple[list[list[list[float]]], list[list[list[float]]]]:
    pending = [segment[:] for segment in segments]
    rings: list[list[list[float]]] = []
    incomplete: list[list[list[float]]] = []

    while pending:
        ring = pending.pop(0)
        while ring[0] != ring[-1]:
            matched = False
            for index, segment in enumerate(pending):
                if ring[-1] == segment[0]:
                    ring.extend(segment[1:])
                elif ring[-1] == segment[-1]:
                    ring.extend(reversed(segment[:-1]))
                elif ring[0] == segment[-1]:
                    ring = segment[:-1] + ring
                elif ring[0] == segment[0]:
                    ring = list(reversed(segment[1:])) + ring
                else:
                    continue
                pending.pop(index)
                matched = True
                break

            if not matched:
                break

        if (
            ring[0] == ring[-1]
            and len(ring) >= 4
            and len({tuple(point) for point in ring[:-1]}) >= 3
        ):
            rings.append(ring)
        else:
            incomplete.append(ring)

    return rings, incomplete


def _point_in_ring(point: list[float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    previous = ring[-1]
    for current in ring:
        if (current[1] > y) != (previous[1] > y):
            crossing_x = (previous[0] - current[0]) * (y - current[1]) / (
                previous[1] - current[1]
            ) + current[0]
            if x < crossing_x:
                inside = not inside
        previous = current
    return inside


def _relation_geometry(
    element: Mapping[str, object],
) -> GeoJSONGeometry | GeoJSONGeometryCollection | None:
    raw_members = element.get("members")
    if not isinstance(raw_members, Sequence) or isinstance(raw_members, (str, bytes)):
        return None

    segments: dict[str, list[list[list[float]]]] = {"outer": [], "inner": []}
    for member in raw_members:
        if not isinstance(member, Mapping) or member.get("type") != "way":
            continue
        role = member.get("role")
        if role not in segments:
            continue
        raw_geometry = member.get("geometry")
        if raw_geometry is None:
            continue
        try:
            coordinates = _coordinates_from_geometry(raw_geometry)
        except ValueError:
            logger.warning("Skipping malformed geometry in OSM relation member")
            continue
        if len(coordinates) >= 2:
            segments[role].append(coordinates)

    outer_rings, incomplete_outer = _stitch_rings(segments["outer"])
    inner_rings, incomplete_inner = _stitch_rings(segments["inner"])
    polygons: list[list[list[list[float]]]] = [
        [_orient_ring(ring, counterclockwise=True)] for ring in outer_rings
    ]

    for inner in inner_rings:
        containing = [
            index
            for index, polygon in enumerate(polygons)
            if _point_in_ring(inner[0], polygon[0])
        ]
        if containing:
            outer_index = min(containing, key=lambda index: abs(_signed_area(polygons[index][0])))
            polygons[outer_index].append(_orient_ring(inner, counterclockwise=False))
        else:
            logger.warning("Skipping OSM relation inner ring with no containing outer ring")

    geometries: list[GeoJSONGeometry | GeoJSONGeometryCollection] = []
    if polygons:
        if len(polygons) == 1:
            geometries.append({"type": "Polygon", "coordinates": polygons[0]})
        else:
            geometries.append({"type": "MultiPolygon", "coordinates": polygons})

    incomplete = incomplete_outer + incomplete_inner
    if incomplete:
        geometries.append({"type": "MultiLineString", "coordinates": incomplete})
    if len(geometries) == 1:
        return geometries[0]
    if geometries:
        return {"type": "GeometryCollection", "geometries": geometries}
    return None


def geometry_from_osm(element: Mapping[str, object]) -> GeoJSONGeometry | GeoJSONGeometryCollection:
    element_type = element.get("type")
    geometry: GeoJSONGeometry | GeoJSONGeometryCollection | None
    if element_type == "node":
        geometry = _element_point(element)
    elif element_type == "way":
        geometry = _way_geometry(element)
    elif element_type == "relation":
        geometry = _relation_geometry(element)
    else:
        raise ValueError(f"Unsupported OSM element type: {element_type!r}")

    if geometry is None:
        center = element.get("center")
        if isinstance(center, Mapping):
            geometry = _element_point(center)
    if geometry is None:
        raise ValueError("OSM element has no usable coordinates or area geometry")
    return geometry
