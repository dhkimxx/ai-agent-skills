from __future__ import annotations

from typing import Any, Dict

ARTICLE_DETAIL_SECTION_KEYS = [
    "articleDetail",
    "articleAddition",
    "articlePrice",
    "articleSpace",
    "articleRealtor",
]


def flatten_article_payload(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    flattened: Dict[str, Any] = {}
    for key in ARTICLE_DETAIL_SECTION_KEYS:
        section = payload.get(key)
        if isinstance(section, dict):
            flattened.update(section)

    if flattened:
        return flattened

    return payload
