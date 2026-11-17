import logging
from dataclasses import dataclass
from typing import Mapping

from app.services.geography import GeoJSONGeometry, GeoJSONGeometryCollection, geometry_from_osm

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NormalizedParking:
    osm_id: str
    name: str | None
    geometry: GeoJSONGeometry | GeoJSONGeometryCollection
    parking_type: str
    fee: str | None
    capacity: int | None
    access: str | None
    supports_car: bool | None
    supports_bike: bool | None
    tags: dict[str, str]
    source: str = "openstreetmap"


def _tag_bool(tags: Mapping[str, str], *keys: str) -> bool | None:
    for key in keys:
        value = tags.get(key, "").strip().lower()
        if value in {"yes", "designated", "permissive"}:
            return True
        if value in {"no", "private", "prohibited"}:
            return False
    return None


def _tags_for(element: Mapping[str, object]) -> dict[str, str]:
    raw_tags = element.get("tags")
    if not isinstance(raw_tags, Mapping):
        return {}
    return {
        str(key): value
        for key, value in raw_tags.items()
        if isinstance(value, str)
    }


def _capacity(tags: Mapping[str, str], osm_id: str) -> int | None:
    value = tags.get("capacity")
    if value is None:
        return None
    try:
        capacity = int(value)
    except ValueError:
        logger.warning("Ignoring invalid capacity on OSM parking feature %s", osm_id)
        return None
    if capacity < 0:
        logger.warning("Ignoring negative capacity on OSM parking feature %s", osm_id)
        return None
    return capacity


def normalize_parking_elements(elements: list[object]) -> tuple[NormalizedParking, ...]:
    normalized: dict[str, NormalizedParking] = {}
    accepted_amenities = {"parking", "motorcycle_parking", "parking_entrance", "parking_space"}

    for element in elements:
        if not isinstance(element, Mapping):
            logger.warning("Skipping invalid Overpass element")
            continue

        element_type = element.get("type")
        osm_value = element.get("id")
        if (
            element_type not in {"node", "way", "relation"}
            or isinstance(osm_value, bool)
            or not isinstance(osm_value, (str, int))
        ):
            logger.warning("Skipping Overpass element without a supported OSM ID")
            continue

        tags = _tags_for(element)
        parking_type = tags.get("amenity", "")
        if parking_type not in accepted_amenities:
            continue

        osm_id = f"{element_type}/{osm_value}"
        if osm_id in normalized:
            continue
        try:
            geometry = geometry_from_osm(element)
        except ValueError as exc:
            logger.warning("Skipping OSM parking feature %s: %s", osm_id, exc)
            continue

        supports_bike = _tag_bool(tags, "motorcycle", "motor_vehicle")
        supports_car = _tag_bool(tags, "motorcar", "motor_vehicle")
        if parking_type == "motorcycle_parking":
            supports_bike = True
            supports_car = False

        normalized.setdefault(
            osm_id,
            NormalizedParking(
                osm_id=osm_id,
                name=tags.get("name") or tags.get("name:en"),
                geometry=geometry,
                parking_type=parking_type,
                fee=tags.get("fee") or tags.get("charge"),
                capacity=_capacity(tags, osm_id),
                access=tags.get("access"),
                supports_car=supports_car,
                supports_bike=supports_bike,
                tags=tags,
            ),
        )

    return tuple(normalized.values())
