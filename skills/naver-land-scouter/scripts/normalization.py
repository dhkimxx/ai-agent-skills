from __future__ import annotations

import re
from typing import Optional

from .constants import PYEONG_TO_SQUARE_METER


MANWON_PER_EOK = 10000
MANWON_PER_CHEON = 1000


def sanitize_numeric_text(value: str) -> str:
    return (
        value.replace(" ", "")
        .replace(",", "")
        .replace("원", "")
        .replace("이하", "")
        .replace("이상", "")
        .replace("미만", "")
        .replace("초과", "")
        .replace("약", "")
        .replace("최대", "")
        .replace("최소", "")
        .replace("㎡", "")
        .replace("m2", "")
        .replace("m²", "")
    )


def parse_float(value: str) -> Optional[float]:
    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return None
    return float(match.group(0))


def normalize_price_to_manwon(value: Optional[float | str]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    text = sanitize_numeric_text(str(value))
    if not text:
        return None

    if "억" in text:
        parts = text.split("억", 1)
        major = parse_float(parts[0]) or 0.0
        minor = parse_manwon_part(parts[1]) if len(parts) > 1 else 0.0
        # 네이버 가격 파라미터는 만원 단위를 기준으로 환산한다.
        return int(major * MANWON_PER_EOK + minor)

    return parse_manwon_part(text)


def parse_manwon_part(text: str) -> Optional[int]:
    if not text:
        return 0

    if "천만" in text:
        numeric = parse_float(text.split("천만", 1)[0])
        if numeric is None:
            return None
        return int(numeric * MANWON_PER_CHEON)

    normalized = text.replace("만", "")
    numeric = parse_float(normalized)
    if numeric is None:
        return None

    if "천" in normalized and "만" not in text:
        # "5천"처럼 천 단위가 남아있을 때만 보정한다.
        return int(numeric * MANWON_PER_CHEON)

    return int(numeric)


def normalize_area_to_square_meter(value: Optional[float | str]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = sanitize_numeric_text(str(value))
    if not text:
        return None

    numeric = parse_float(text)
    if numeric is None:
        return None

    if "평" in text:
        # 평 단위를 기본 m2 스펙에 맞추기 위해 변환한다.
        return round(numeric * PYEONG_TO_SQUARE_METER, 2)

    return float(numeric)
