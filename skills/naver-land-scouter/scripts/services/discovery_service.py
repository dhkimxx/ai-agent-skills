from __future__ import annotations

import re
from typing import Any, List, Optional

from ..location_utils import calculate_distance_meters, infer_dong_name, pick_first_text
from ..normalization import normalize_area_to_square_meter, normalize_price_to_manwon
from ..param_builder import build_cortars_params, build_marker_params
from ..schemas import (
    BoundingBox,
    FilterDropReason,
    FilterStats,
    ListingResult,
    NormalizedArticle,
    RawComplexDetail,
    RawComplexMarker,
    RawComplexOverview,
)
from .contracts import NaverLandRepository
from .errors import ServiceError, build_service_error


class DiscoveryService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def discover_by_map(
        self,
        center_lat: float,
        center_lon: float,
        zoom: int,
        bounding_box: BoundingBox,
        real_estate_type: str,
        price_type: Optional[str] = None,
        is_presale: Optional[bool] = None,
        enrich_mode: Optional[str] = None,
        radius_meters: Optional[int] = None,
    ) -> ListingResult:
        try:
            cortars_params = build_cortars_params(center_lat, center_lon, zoom)
            cortars_payload, cortars_context = self._repository.fetch_cortars(
                cortars_params
            )
            cortar_no = _extract_cortar_no(cortars_payload)

            marker_params = build_marker_params(
                cortar_no=cortar_no,
                bounding_box=bounding_box,
                zoom=zoom,
                real_estate_type=real_estate_type,
                price_type=price_type,
                is_presale=is_presale,
            )
            marker_payload, marker_context = self._repository.fetch_complex_markers(
                marker_params
            )

            listing_result = _extract_listing_from_markers(
                marker_payload,
                center_lat=center_lat,
                center_lon=center_lon,
            )
            listing_result = _filter_listing_by_radius(listing_result, radius_meters)
            extra_sources = []
            if enrich_mode == "complex-summary":
                extra_sources = self._enrich_complex_summaries(listing_result.items)
            listing_result.sources.extend([cortars_context, marker_context])
            listing_result.sources.extend(extra_sources)
            return listing_result
        except ServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - 서비스 공통 에러로 변환한다.
            raise build_service_error(
                exc,
                error_code="DISCOVERY_FAILED",
                message="지도 기반 탐색에 실패했습니다.",
                details={
                    "center_lat": center_lat,
                    "center_lon": center_lon,
                    "zoom": zoom,
                    "enrich_mode": enrich_mode,
                    "radius_meters": radius_meters,
                },
            ) from exc

    def _enrich_complex_summaries(self, items: List[NormalizedArticle]) -> List[Any]:
        sources = []
        for item in items:
            if not item.complex_no:
                continue
            try:
                overview_payload, overview_context = self._repository.fetch_complex_overview(
                    item.complex_no
                )
                detail_payload, detail_context = self._repository.fetch_complex_detail(
                    item.complex_no
                )
            except Exception:
                continue

            _apply_complex_summary(item, overview_payload, detail_payload)
            sources.extend([overview_context, detail_context])
        return sources


def _extract_cortar_no(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ["cortarNo", "cortarNoList", "cortarnolist"]:
            value = payload.get(key)
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict) and first.get("cortarNo"):
                    return str(first.get("cortarNo"))
                if isinstance(first, str):
                    return first
            if isinstance(value, str):
                return value
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict) and first.get("cortarNo"):
            return str(first.get("cortarNo"))
    raise ServiceError(
        error_code="CORTAR_NOT_FOUND",
        message="행정구역 코드(cortarNo)를 찾지 못했습니다.",
    )


def _extract_listing_from_markers(
    payload: Any,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
) -> ListingResult:
    if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
        error = payload.get("error") or {}
        raise ServiceError(
            error_code="DISCOVERY_MARKER_ERROR",
            message=error.get("message") or "지도 마커 응답에 오류가 포함되었습니다.",
            details={"code": error.get("code")},
        )

    items: List[NormalizedArticle] = []
    if isinstance(payload, dict):
        for key in ["markers", "complexes", "list", "result"]:
            value = payload.get(key)
            if isinstance(value, list):
                items.extend(_extract_marker_items(value, center_lat, center_lon))
                break
    elif isinstance(payload, list):
        items.extend(_extract_marker_items(payload, center_lat, center_lon))

    return ListingResult(query_text="discover", items=items)


def _extract_marker_items(
    raw_items: List[Any],
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
) -> List[NormalizedArticle]:
    items: List[NormalizedArticle] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        parsed = RawComplexMarker.model_validate(item)
        price = (
            parsed.median_deal_price
            or parsed.min_deal_price
            or parsed.max_deal_price
        )
        representative_area = _resolve_representative_area(parsed)
        address = _resolve_marker_address(item, parsed)
        dong_name = parsed.dong_name or infer_dong_name(
            item.get("sectionName"),
            item.get("divisionName"),
            item.get("cortarName"),
            address,
        )
        items.append(
            NormalizedArticle(
                complex_no=parsed.complex_no or parsed.marker_id,
                article_name=parsed.complex_name,
                price=normalize_price_to_manwon(price),
                trade_type="A1" if (parsed.deal_count or 0) > 0 else None,
                real_estate_type=parsed.real_estate_type_code,
                area=representative_area,
                exclusive_area=representative_area,
                address=address,
                dong_name=dong_name,
                latitude=parsed.latitude,
                longitude=parsed.longitude,
                distance_meters=calculate_distance_meters(
                    center_lat,
                    center_lon,
                    parsed.latitude,
                    parsed.longitude,
                ),
                article_feature_description=_build_marker_summary(parsed),
            )
        )
    return items


def _resolve_representative_area(marker: RawComplexMarker) -> Optional[float]:
    if marker.representative_area is not None:
        return float(marker.representative_area)

    min_area = normalize_area_to_square_meter(marker.min_area)
    max_area = normalize_area_to_square_meter(marker.max_area)
    if min_area is not None and max_area is not None:
        return round((min_area + max_area) / 2, 2)
    return min_area or max_area


def _build_marker_summary(marker: RawComplexMarker) -> Optional[str]:
    summary_parts: List[str] = []
    if marker.total_article_count is not None:
        summary_parts.append(f"총 {marker.total_article_count}건")
    if marker.deal_count is not None:
        summary_parts.append(f"매매 {marker.deal_count}건")
    if marker.lease_count is not None:
        summary_parts.append(f"전세 {marker.lease_count}건")
    if marker.rent_count is not None:
        summary_parts.append(f"월세 {marker.rent_count}건")
    if not summary_parts:
        return None
    return ", ".join(summary_parts)


def _filter_listing_by_radius(
    listing_result: ListingResult,
    radius_meters: Optional[int],
) -> ListingResult:
    if radius_meters is None:
        return listing_result

    before_count = len(listing_result.items)
    filtered_items = [
        item
        for item in listing_result.items
        if item.distance_meters is None or item.distance_meters <= radius_meters
    ]
    excluded_count = before_count - len(filtered_items)

    listing_result.items = filtered_items
    listing_result.filter_stats = FilterStats(
        before_count=before_count,
        after_count=len(filtered_items),
        drop_reasons=[
            FilterDropReason(
                filter_name="radius_meters",
                excluded_count=excluded_count,
                description="반경 조건을 초과해 제외된 단지 수입니다.",
            )
        ]
        if excluded_count > 0
        else [],
    )
    return listing_result


def _apply_complex_summary(
    item: NormalizedArticle,
    overview_payload: Any,
    detail_payload: Any,
) -> None:
    overview_raw = overview_payload if isinstance(overview_payload, dict) else {}
    detail_container = detail_payload if isinstance(detail_payload, dict) else {}
    detail_raw = (
        detail_container.get("complexDetail")
        if isinstance(detail_container.get("complexDetail"), dict)
        else detail_container
    )

    overview = RawComplexOverview.model_validate(overview_raw)
    detail = RawComplexDetail.model_validate(detail_raw)

    total_household_count = (
        detail.total_household_count
        or overview.total_household_count
        or item.total_household_count
    )
    item.total_household_count = total_household_count
    item.total_building_count = detail.total_building_count or item.total_building_count
    item.completion_year = (
        _resolve_completion_year(detail.completion_year)
        or _resolve_completion_year(overview.completion_year)
        or item.completion_year
    )
    item.parking_count = (
        detail.parking_count
        or _resolve_parking_count(detail.parking_count_by_household, total_household_count)
        or item.parking_count
    )
    item.address = item.address or detail.address or overview.address
    item.latitude = item.latitude or detail.latitude or overview.latitude
    item.longitude = item.longitude or detail.longitude or overview.longitude


def _resolve_completion_year(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if value > 10_000:
        return int(str(value)[:4])
    return value


def _resolve_parking_count(
    parking_count_by_household: Optional[float],
    total_household_count: Optional[int],
) -> Optional[int]:
    if parking_count_by_household is None or total_household_count is None:
        return None
    return int(round(parking_count_by_household * total_household_count))


def _resolve_marker_address(
    raw_marker: dict,
    parsed_marker: RawComplexMarker,
) -> Optional[str]:
    address = pick_first_text(
        parsed_marker.address,
        raw_marker.get("jibunAddress"),
        raw_marker.get("roadAddress"),
        raw_marker.get("address"),
    )
    if address:
        return address

    address_parts = [
        raw_marker.get("cityName"),
        raw_marker.get("divisionName"),
        raw_marker.get("sectionName"),
    ]
    joined = " ".join(str(part).strip() for part in address_parts if part)
    return re.sub(r"\s+", " ", joined).strip() or None
