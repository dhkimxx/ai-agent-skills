from __future__ import annotations

import math
import re
from typing import Optional

from .schemas import BoundingBox

EARTH_RADIUS_METERS = 6_371_000
DONG_NAME_PATTERN = re.compile(r"([가-힣A-Za-z0-9]+동)")
METER_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(m|km)?\s*$", re.IGNORECASE)


def calculate_distance_meters(
    origin_lat: Optional[float],
    origin_lon: Optional[float],
    target_lat: Optional[float],
    target_lon: Optional[float],
) -> Optional[int]:
    if None in {origin_lat, origin_lon, target_lat, target_lon}:
        return None

    origin_lat_rad = math.radians(float(origin_lat))
    origin_lon_rad = math.radians(float(origin_lon))
    target_lat_rad = math.radians(float(target_lat))
    target_lon_rad = math.radians(float(target_lon))

    delta_lat = target_lat_rad - origin_lat_rad
    delta_lon = target_lon_rad - origin_lon_rad

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(origin_lat_rad)
        * math.cos(target_lat_rad)
        * math.sin(delta_lon / 2) ** 2
    )
    distance = 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(haversine))
    return int(round(distance))


def pick_first_text(*candidates: object) -> Optional[str]:
    for candidate in candidates:
        if isinstance(candidate, str):
            normalized = candidate.strip()
            if normalized:
                return normalized
    return None


def infer_dong_name(*candidates: object) -> Optional[str]:
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        match = DONG_NAME_PATTERN.search(candidate)
        if match:
            return match.group(1)
    return None


def parse_radius_to_meters(value: Optional[str | int | float]) -> int:
    if value is None:
        return 500
    if isinstance(value, (int, float)):
        return max(1, int(round(float(value))))

    match = METER_PATTERN.match(str(value))
    if not match:
        raise ValueError(f"지원하지 않는 반경 형식입니다: {value}")

    numeric = float(match.group(1))
    unit = (match.group(2) or "m").lower()
    if unit == "km":
        numeric *= 1000
    return max(1, int(round(numeric)))


def build_bounding_box_from_radius(
    center_lat: float,
    center_lon: float,
    radius_meters: int,
) -> BoundingBox:
    lat_delta = radius_meters / 111_320
    cos_lat = math.cos(math.radians(center_lat))
    lon_denominator = 111_320 * cos_lat if abs(cos_lat) > 1e-6 else 111_320
    lon_delta = radius_meters / lon_denominator
    return BoundingBox(
        left_lon=round(center_lon - lon_delta, 7),
        right_lon=round(center_lon + lon_delta, 7),
        top_lat=round(center_lat + lat_delta, 7),
        bottom_lat=round(center_lat - lat_delta, 7),
    )


def parse_map_search_deep_link(
    deep_link: Optional[str],
) -> tuple[Optional[float], Optional[float], Optional[int]]:
    if not deep_link:
        return None, None, None

    match = re.search(r"[?&]ms=([0-9.]+),([0-9.]+),(\d+)", deep_link)
    if not match:
        return None, None, None

    return float(match.group(1)), float(match.group(2)), int(match.group(3))
