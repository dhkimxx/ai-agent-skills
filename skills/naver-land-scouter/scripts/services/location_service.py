from __future__ import annotations

from typing import Any, List, Optional

from ..location_utils import (
    build_bounding_box_from_radius,
    parse_map_search_deep_link,
)
from ..schemas import (
    NormalizedComplex,
    RawSearchComplex,
    RawSearchRegion,
    ResolvedLocation,
    SearchResult,
)
from .contracts import NaverLandRepository
from .discovery_service import DiscoveryService
from .errors import ServiceError, build_service_error


class LocationService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def search(
        self,
        query_text: str,
        radius_meters: int = 700,
        real_estate_type: str = "APT",
        enrich_mode: Optional[str] = None,
    ) -> SearchResult:
        try:
            payload, context = self._repository.fetch_search(
                {"keyword": query_text, "page": 1}
            )
            candidates = _extract_location_candidates(query_text, payload)
            complexes = _extract_search_complexes(payload)

            nearby_complexes = []
            if len(candidates) == 1:
                candidate = candidates[0]
                bbox = build_bounding_box_from_radius(
                    candidate.latitude,
                    candidate.longitude,
                    radius_meters,
                )
                nearby_result = DiscoveryService(self._repository).discover_by_map(
                    center_lat=candidate.latitude,
                    center_lon=candidate.longitude,
                    zoom=candidate.zoom or 16,
                    bounding_box=bbox,
                    real_estate_type=real_estate_type,
                    enrich_mode=enrich_mode,
                    radius_meters=radius_meters,
                )
                nearby_complexes = nearby_result.items

            return SearchResult(
                query_text=query_text,
                candidates=candidates,
                complexes=complexes,
                nearby_complexes=nearby_complexes,
                sources=[context],
            )
        except ServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - 검색 단계도 공통 에러 포맷으로 변환한다.
            raise build_service_error(
                exc,
                error_code="LOCATION_SEARCH_FAILED",
                message="위치 검색에 실패했습니다.",
                details={"query_text": query_text},
            ) from exc

    def resolve_single_location(self, query_text: str) -> ResolvedLocation:
        payload, context = self._repository.fetch_search({"keyword": query_text, "page": 1})
        candidates = _extract_location_candidates(query_text, payload)
        if not candidates:
            raise ServiceError(
                error_code="LOCATION_NOT_FOUND",
                message="검색어에 해당하는 위치를 찾지 못했습니다.",
                details={"query_text": query_text},
            )
        if len(candidates) > 1:
            raise ServiceError(
                error_code="LOCATION_AMBIGUOUS",
                message="검색어가 여러 위치로 해석됩니다. 더 구체적으로 입력하세요.",
                details={
                    "query_text": query_text,
                    "candidates": [candidate.model_dump(by_alias=True, exclude_none=True) for candidate in candidates],
                    "source": context.model_dump(by_alias=True, exclude_none=True),
                },
            )
        return candidates[0]


def _extract_location_candidates(query_text: str, payload: Any) -> List[ResolvedLocation]:
    if not isinstance(payload, dict):
        return []

    candidates: List[ResolvedLocation] = []
    for item in payload.get("regions") or []:
        if not isinstance(item, dict):
            continue
        parsed = RawSearchRegion.model_validate(item)
        if parsed.center_lat is None or parsed.center_lon is None:
            continue
        candidates.append(
            ResolvedLocation(
                query_text=query_text,
                label=parsed.cortar_name or query_text,
                latitude=parsed.center_lat,
                longitude=parsed.center_lon,
                zoom=_resolve_zoom(parsed.deep_link),
                deep_link=parsed.deep_link,
                cortar_no=parsed.cortar_no,
                address=parsed.cortar_name,
                match_type=parsed.cortar_type or "region",
            )
        )

    if candidates:
        return _deduplicate_candidates(candidates)

    deep_link = payload.get("deepLink")
    latitude, longitude, zoom = parse_map_search_deep_link(deep_link)
    if latitude is not None and longitude is not None:
        return [
            ResolvedLocation(
                query_text=query_text,
                label=query_text,
                latitude=latitude,
                longitude=longitude,
                zoom=zoom or 16,
                deep_link=deep_link,
                match_type="landmark",
            )
        ]

    complexes = _extract_search_complexes(payload)
    if len(complexes) == 1 and complexes[0].latitude is not None and complexes[0].longitude is not None:
        complex_item = complexes[0]
        return [
            ResolvedLocation(
                query_text=query_text,
                label=complex_item.complex_name or query_text,
                latitude=complex_item.latitude,
                longitude=complex_item.longitude,
                zoom=16,
                address=complex_item.address,
                match_type="complex",
            )
        ]

    return []


def _extract_search_complexes(payload: Any) -> List[NormalizedComplex]:
    if not isinstance(payload, dict):
        return []

    complexes: List[NormalizedComplex] = []
    for item in payload.get("complexes") or []:
        if not isinstance(item, dict):
            continue
        parsed = RawSearchComplex.model_validate(item)
        complexes.append(
            NormalizedComplex(
                complex_no=parsed.complex_no,
                complex_name=parsed.complex_name,
                address=parsed.cortar_address,
                latitude=parsed.latitude,
                longitude=parsed.longitude,
                total_household_count=parsed.total_household_count,
                total_building_count=parsed.total_dong_count,
                completion_year=_resolve_completion_year(parsed.use_approve_ymd),
            )
        )
    return complexes


def _resolve_zoom(deep_link: Optional[str]) -> int:
    _, _, zoom = parse_map_search_deep_link(deep_link)
    return zoom or 16


def _resolve_completion_year(use_approve_ymd: Optional[str]) -> Optional[int]:
    if not use_approve_ymd or len(use_approve_ymd) < 4:
        return None
    try:
        return int(use_approve_ymd[:4])
    except ValueError:
        return None


def _deduplicate_candidates(candidates: List[ResolvedLocation]) -> List[ResolvedLocation]:
    unique_candidates: List[ResolvedLocation] = []
    seen_keys = set()
    for candidate in candidates:
        key = (
            round(candidate.latitude or 0, 6),
            round(candidate.longitude or 0, 6),
            candidate.label,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_candidates.append(candidate)
    return unique_candidates
