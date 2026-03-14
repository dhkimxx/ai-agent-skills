from __future__ import annotations

from typing import Any, List, Optional

from ..normalization import normalize_price_to_manwon
from ..param_builder import build_cortars_params, build_marker_params
from ..schemas import BoundingBox, ListingResult, NormalizedArticle
from .contracts import NaverLandRepository
from .errors import ServiceError


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
            raise ServiceError(
                error_code="DISCOVERY_FAILED",
                message="지도 기반 탐색에 실패했습니다.",
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
        items.append(
            NormalizedArticle(
                complex_no=str(item.get("complexNo")) if item.get("complexNo") else None,
                article_name=item.get("complexName") or item.get("name"),
                price=normalize_price_to_manwon(item.get("dealPrice")),
                trade_type=item.get("tradeType"),
            )
        )
    return items
