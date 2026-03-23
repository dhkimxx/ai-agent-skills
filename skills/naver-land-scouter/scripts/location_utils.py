from __future__ import annotations

import math
import re
from typing import Optional


EARTH_RADIUS_METERS = 6_371_000
DONG_NAME_PATTERN = re.compile(r"([가-힣A-Za-z0-9]+동)")


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
