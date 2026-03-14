from __future__ import annotations

import re
from typing import Optional, Tuple

from .constants import PYEONG_TO_SQUARE_METER
from .normalization import parse_float

UNIT_PATTERN = re.compile(r"(㎡|m2|m²|평대|평)", re.IGNORECASE)


def parse_area_range(value: Optional[float | str]) -> Optional[Tuple[float, float]]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        converted = float(value)
        return (
            _to_square_meter(converted, unit="pyeong"),
            _to_square_meter(converted, unit="pyeong"),
        )

    raw = str(value)
    unit = _detect_unit(raw)

    range_expression = parse_area_range_expression(raw)
    if range_expression:
        return range_expression

    numeric = parse_float(raw)
    if numeric is None:
        return None

    return (_to_square_meter(numeric, unit=unit), _to_square_meter(numeric, unit=unit))


def parse_area_range_expression(value: Optional[float | str]) -> Optional[Tuple[float, float]]:
    if value is None:
        return None

    raw = str(value)
    compact = raw.replace(" ", "")
    unit = _detect_unit(raw)

    if "평대" in compact:
        numeric = parse_float(compact)
        if numeric is None:
            return None
        lower = numeric
        upper = numeric + 9
        return (
            _to_square_meter(lower, unit="pyeong"),
            _to_square_meter(upper, unit="pyeong"),
        )

    cleaned = _strip_unit_tokens(raw)
    numbers = _extract_numbers(cleaned)
    if len(numbers) >= 2:
        lower = min(numbers[0], numbers[1])
        upper = max(numbers[0], numbers[1])
        return (_to_square_meter(lower, unit=unit), _to_square_meter(upper, unit=unit))

    if _contains_range_separator(cleaned) and numbers:
        value_number = numbers[0]
        return (
            _to_square_meter(value_number, unit=unit),
            _to_square_meter(value_number, unit=unit),
        )

    return None


def _strip_unit_tokens(text: str) -> str:
    return UNIT_PATTERN.sub(" ", text)


def _extract_numbers(text: str) -> list[float]:
    return [float(value) for value in re.findall(r"\d+(?:\.\d+)?", text)]


def _contains_range_separator(text: str) -> bool:
    return any(separator in text for separator in ["~", "-", ",", " "])


def _detect_unit(text: str) -> str:
    lowered = text.lower()
    if "평" in lowered:
        return "pyeong"
    if "㎡" in lowered or "m2" in lowered or "m²" in lowered:
        return "sqm"
    return "pyeong"


def _to_square_meter(value: float, unit: str) -> float:
    if unit == "pyeong":
        return round(value * PYEONG_TO_SQUARE_METER, 2)
    return float(value)
