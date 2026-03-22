from __future__ import annotations

from typing import Any, List, Optional

from ..normalization import normalize_area_to_square_meter, normalize_price_to_manwon
from ..param_builder import build_cortars_params, build_marker_params
from ..schemas import BoundingBox, ListingResult, NormalizedArticle, RawComplexMarker
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

            listing_result = _extract_listing_from_markers(marker_payload)
            listing_result.sources.extend([cortars_context, marker_context])
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
                },
            ) from exc


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


def _extract_listing_from_markers(payload: Any) -> ListingResult:
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
                items.extend(_extract_marker_items(value))
                break
    elif isinstance(payload, list):
        items.extend(_extract_marker_items(payload))

    return ListingResult(query_text="discover", items=items)


def _extract_marker_items(raw_items: List[Any]) -> List[NormalizedArticle]:
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
        items.append(
            NormalizedArticle(
                complex_no=parsed.marker_id,
                article_name=parsed.complex_name,
                price=normalize_price_to_manwon(price),
                trade_type="A1" if (parsed.deal_count or 0) > 0 else None,
                real_estate_type=parsed.real_estate_type_code,
                area=representative_area,
                exclusive_area=representative_area,
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
