from __future__ import annotations

from collections import defaultdict
from typing import List, Optional

from ..location_utils import build_bounding_box_from_radius
from ..schemas import (
    FilterDropReason,
    FilterStats,
    ListingSearchInput,
    NormalizedArticle,
    ScanResult,
    ScanTargetResult,
)
from .contracts import NaverLandRepository
from .discovery_service import DiscoveryService
from .errors import ServiceError, build_service_error
from .listing_service import ListingService
from .location_service import LocationService


class ScanService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def scan_near_queries(
        self,
        near_queries: List[str],
        radius_meters: int,
        real_estate_type: str,
        listing_input: Optional[ListingSearchInput] = None,
        enrich_mode: Optional[str] = None,
        complex_limit: int = 12,
        expand_articles: bool = False,
        region_hint: Optional[str] = None,
    ) -> ScanResult:
        try:
            location_service = LocationService(self._repository)
            discovery_service = DiscoveryService(self._repository)
            listing_service = ListingService(self._repository)

            targets: List[ScanTargetResult] = []
            merged_items: List[NormalizedArticle] = []
            aggregated_sources = []
            per_filter_before = 0
            per_filter_after = 0
            drop_reason_counts: dict[str, int] = defaultdict(int)
            drop_reason_descriptions: dict[str, str] = {}
            warnings: List[str] = []

            for query_text in near_queries:
                target_result = ScanTargetResult(
                    query_text=query_text,
                    status="pending",
                )
                try:
                    resolution_bundle = location_service.resolve_location_bundle(
                        query_text,
                        region_hint=region_hint,
                    )
                    aggregated_sources.extend(resolution_bundle.sources)
                    decision = resolution_bundle.decision
                    if decision.preferred_candidate is None:
                        raise ServiceError(
                            error_code="LOCATION_AMBIGUOUS",
                            message="검색어가 여러 위치로 해석됩니다. 더 구체적으로 입력하세요.",
                            details={
                                "query_text": query_text,
                                "query_intent": decision.query_intent,
                                "region_hint": decision.region_hint,
                                "ambiguity_reason": decision.ambiguity_reason,
                            },
                        )

                    resolved = decision.preferred_candidate
                    target_result.resolved_location = resolved
                    target_result.resolution_strategy = decision.resolution_strategy
                    target_result.warnings.extend(decision.warnings)
                    warnings.extend(
                        f"{query_text}: {warning_message}"
                        for warning_message in decision.warnings
                    )

                    bbox = build_bounding_box_from_radius(
                        resolved.latitude,
                        resolved.longitude,
                        radius_meters,
                    )
                    discovered = discovery_service.discover_by_map(
                        center_lat=resolved.latitude,
                        center_lon=resolved.longitude,
                        zoom=resolved.zoom or 16,
                        bounding_box=bbox,
                        real_estate_type=real_estate_type,
                        enrich_mode=enrich_mode,
                        radius_meters=radius_meters,
                    )
                    aggregated_sources.extend(discovered.sources)
                    target_result.complexes = discovered.items
                    target_result.status = "success"
                except ServiceError as exc:
                    target_result.status = "failed"
                    target_result.error_code = exc.error_code
                    target_result.error_message = exc.message
                    if exc.details and exc.details.get("ambiguity_reason"):
                        target_result.warnings.append(exc.details["ambiguity_reason"])
                    warnings.append(f"{query_text}: {exc.error_code}")
                    targets.append(target_result)
                    continue
                except Exception as exc:  # noqa: BLE001 - 타겟 단위 실패로 격리한다.
                    service_error = build_service_error(
                        exc,
                        error_code="SCAN_TARGET_FAILED",
                        message="개별 검색 타겟 처리에 실패했습니다.",
                        details={"query_text": query_text},
                    )
                    target_result.status = "failed"
                    target_result.error_code = service_error.error_code
                    target_result.error_message = service_error.message
                    warnings.append(f"{query_text}: {service_error.error_code}")
                    targets.append(target_result)
                    continue

                if expand_articles and listing_input is not None:
                    target_articles: List[NormalizedArticle] = []
                    per_target_input = listing_input.model_copy(
                        update={
                            "center_lat": resolved.latitude,
                            "center_lon": resolved.longitude,
                            "real_estate_type": listing_input.real_estate_type
                            or real_estate_type,
                        }
                    )
                    ranked_complexes = sorted(
                        discovered.items,
                        key=lambda item: (
                            item.distance_meters if item.distance_meters is not None else 999999,
                            item.price if item.price is not None else 999999,
                        ),
                    )[:complex_limit]

                    for complex_item in ranked_complexes:
                        if not complex_item.complex_no:
                            continue
                        try:
                            listing_result = listing_service.search_by_complex(
                                complex_item.complex_no,
                                per_target_input,
                            )
                            aggregated_sources.extend(listing_result.sources)
                            target_articles.extend(listing_result.items)
                            if listing_result.filter_stats:
                                per_filter_before += listing_result.filter_stats.before_count
                                per_filter_after += listing_result.filter_stats.after_count
                                for reason in listing_result.filter_stats.drop_reasons:
                                    drop_reason_counts[reason.filter_name] += reason.excluded_count
                                    if reason.description:
                                        drop_reason_descriptions[reason.filter_name] = reason.description
                        except ServiceError as exc:
                            target_result.status = "partial"
                            target_result.warnings.append(
                                f"{complex_item.complex_name or complex_item.complex_no}: {exc.error_code}"
                            )
                            warnings.append(
                                f"{query_text}/{complex_item.complex_no}: {exc.error_code}"
                            )
                        except Exception as exc:  # noqa: BLE001 - 개별 단지 실패는 전체를 중단하지 않는다.
                            service_error = build_service_error(
                                exc,
                                error_code="SCAN_COMPLEX_LISTING_FAILED",
                                message="개별 단지 매물 확장에 실패했습니다.",
                                details={"query_text": query_text, "complex_no": complex_item.complex_no},
                            )
                            target_result.status = "partial"
                            target_result.warnings.append(
                                f"{complex_item.complex_name or complex_item.complex_no}: {service_error.error_code}"
                            )
                            warnings.append(
                                f"{query_text}/{complex_item.complex_no}: {service_error.error_code}"
                            )

                    target_result.articles = _deduplicate_articles(target_articles)

                targets.append(target_result)
                merged_items.extend(
                    target_result.articles if expand_articles else target_result.complexes
                )

            filter_stats = None
            if expand_articles:
                filter_stats = FilterStats(
                    before_count=per_filter_before,
                    after_count=per_filter_after,
                    drop_reasons=[
                        FilterDropReason(
                            filter_name=filter_name,
                            excluded_count=excluded_count,
                            description=drop_reason_descriptions.get(filter_name),
                        )
                        for filter_name, excluded_count in sorted(drop_reason_counts.items())
                    ],
                )

            return ScanResult(
                targets=targets,
                items=_deduplicate_articles(merged_items),
                filter_stats=filter_stats,
                warnings=warnings,
                sources=aggregated_sources,
            )
        except Exception as exc:  # noqa: BLE001 - 서비스 공통 포맷으로 변환한다.
            raise build_service_error(
                exc,
                error_code="SCAN_FAILED",
                message="멀티 영역 통합 검색에 실패했습니다.",
                details={"near_queries": near_queries},
            ) from exc


def _deduplicate_articles(items: List[NormalizedArticle]) -> List[NormalizedArticle]:
    unique_items: dict[tuple[Optional[str], Optional[str], Optional[str]], NormalizedArticle] = {}
    for item in items:
        key = (item.article_no, item.complex_no, item.article_name)
        unique_items[key] = item
    return list(unique_items.values())
