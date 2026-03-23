from __future__ import annotations

import re
from typing import Any, List, Optional

from ..location_utils import calculate_distance_meters, infer_dong_name, pick_first_text
from ..normalization import normalize_price_to_manwon
from ..param_builder import build_article_list_params, resolve_area_range_bounds
from ..schemas import (
    ListingResult,
    ListingSearchInput,
    NormalizedArticle,
    RawArticleSummary,
    RawComplexDetail,
)
from .contracts import NaverLandRepository
from .errors import build_service_error


class ListingService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def search_by_complex(
        self,
        complex_no: str,
        listing_input: ListingSearchInput,
        price_type: str | None = None,
        show_article: bool | None = None,
        same_address_group: bool | None = None,
    ) -> ListingResult:
        try:
            params = build_article_list_params(
                complex_no=complex_no,
                listing_input=listing_input,
                price_type=price_type,
                show_article=show_article,
                same_address_group=same_address_group,
            )
            payload, context = self._repository.fetch_articles_by_complex(
                complex_no, params
            )
            raw_items = _extract_article_items(payload)
            location_fallback, location_context = self._fetch_complex_location_fallback(
                complex_no
            )
            normalized_items = [
                _normalize_article_summary(
                    item,
                    complex_no=complex_no,
                    location_fallback=location_fallback,
                    center_lat=listing_input.center_lat,
                    center_lon=listing_input.center_lon,
                )
                for item in raw_items
            ]
            normalized_items = _filter_by_exclusive_area(
                normalized_items,
                listing_input.exclusive_area_range,
            )
            sources = [context]
            if location_context:
                sources.append(location_context)
            return ListingResult(
                query_text=listing_input.query_text,
                items=normalized_items,
                sources=sources,
            )
        except Exception as exc:  # noqa: BLE001 - 서비스 레이어에서 공통 포맷으로 변환한다.
            raise build_service_error(
                exc,
                error_code="LISTING_SEARCH_FAILED",
                message="매물 검색에 실패했습니다.",
                details={"complex_no": complex_no},
            ) from exc

    def _fetch_complex_location_fallback(
        self,
        complex_no: str,
    ) -> tuple[dict[str, Any], Optional[Any]]:
        try:
            payload, context = self._repository.fetch_complex_detail(complex_no)
        except Exception:  # noqa: BLE001 - 위치 메타데이터는 보조 정보라 조회 실패를 무시한다.
            return {}, None

        parsed = RawComplexDetail.model_validate(payload) if isinstance(payload, dict) else RawComplexDetail()
        return (
            {
                "address": _resolve_address_text(payload if isinstance(payload, dict) else {}, parsed.address),
                "dong_name": parsed.dong_name
                or infer_dong_name(
                    payload.get("sectionName") if isinstance(payload, dict) else None,
                    payload.get("divisionName") if isinstance(payload, dict) else None,
                    parsed.address,
                ),
                "latitude": parsed.latitude,
                "longitude": parsed.longitude,
            },
            context,
        )


def _extract_article_items(payload: Any) -> List[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    candidates = [
        "articleList",
        "articles",
        "list",
        "result",
        "body",
    ]

    for key in candidates:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = value.get("articleList") or value.get("list")
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]

    return []


def _normalize_article_summary(
    raw: dict,
    *,
    complex_no: str,
    location_fallback: dict[str, Any],
    center_lat: Optional[float],
    center_lon: Optional[float],
) -> NormalizedArticle:
    parsed = RawArticleSummary.model_validate(raw)
    address = _resolve_address_text(raw, parsed.address or location_fallback.get("address"))
    dong_name = parsed.dong_name or infer_dong_name(
        raw.get("sectionName"),
        raw.get("divisionName"),
        raw.get("cortarName"),
        address,
        location_fallback.get("dong_name"),
    )
    latitude = parsed.latitude or location_fallback.get("latitude")
    longitude = parsed.longitude or location_fallback.get("longitude")
    return NormalizedArticle(
        article_no=parsed.article_no,
        complex_no=parsed.complex_no or complex_no,
        article_name=parsed.article_name,
        trade_type=parsed.trade_type,
        real_estate_type=parsed.real_estate_type,
        price=normalize_price_to_manwon(parsed.deal_price or parsed.price),
        rent_price=normalize_price_to_manwon(parsed.rent_price),
        area=parsed.area or parsed.exclusive_area,
        exclusive_area=parsed.exclusive_area,
        supply_area=parsed.supply_area,
        floor_info=parsed.floor_info,
        direction=parsed.direction,
        address=address,
        dong_name=dong_name,
        latitude=latitude,
        longitude=longitude,
        distance_meters=calculate_distance_meters(
            center_lat,
            center_lon,
            latitude,
            longitude,
        ),
        article_feature_description=parsed.article_feature_description,
    )


def _filter_by_exclusive_area(
    articles: List[NormalizedArticle],
    exclusive_area_range: Any,
) -> List[NormalizedArticle]:
    if not exclusive_area_range:
        return articles

    lower, upper = resolve_area_range_bounds(
        exclusive_area_range.minimum,
        exclusive_area_range.maximum,
    )
    if lower is None and upper is None:
        return articles

    filtered: List[NormalizedArticle] = []
    for article in articles:
        area = article.exclusive_area or article.area
        if area is None:
            continue
        if lower is not None and area < lower:
            continue
        if upper is not None and area > upper:
            continue
        filtered.append(article)
    return filtered


def _resolve_address_text(raw: dict, fallback: Optional[str]) -> Optional[str]:
    address = pick_first_text(
        raw.get("address"),
        raw.get("jibunAddress"),
        raw.get("roadAddress"),
        fallback,
    )
    if address:
        return address

    address_parts = [
        raw.get("cityName"),
        raw.get("divisionName"),
        raw.get("sectionName"),
    ]
    joined = " ".join(str(part).strip() for part in address_parts if part)
    return re.sub(r"\s+", " ", joined).strip() or None
