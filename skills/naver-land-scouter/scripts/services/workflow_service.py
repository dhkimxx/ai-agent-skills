from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from ..constants import PYEONG_TO_SQUARE_METER
from ..normalization import normalize_price_to_manwon
from ..param_builder import resolve_area_range_bounds
from ..schemas import (
    ApiRequestContext,
    AreaRange,
    HistoryInput,
    ListingSearchInput,
    NormalizedArticle,
    PremiumSummary,
    PriceRange,
    ScanResult,
    WorkflowAttemptSummary,
    WorkflowRecommendedItem,
    WorkflowRequest,
    WorkflowResult,
)
from .contracts import NaverLandRepository
from .errors import ServiceError, build_service_error
from .history_service import HistoryService
from .scan_service import ScanService

PRICE_RELAXATION_DELTA_MANWON = 5000
AREA_RELAXATION_DELTA_SQUARE_METER = round(PYEONG_TO_SQUARE_METER * 5, 2)


@dataclass(frozen=True)
class WorkflowExecutionPlan:
    radius_meters: int
    listing_input: ListingSearchInput
    relaxation_stage: str
    applied_filters: List[str]


class WorkflowService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def run_listing_workflow(
        self,
        near_queries: List[str],
        radius_meters: int,
        real_estate_type: str,
        listing_input: Optional[ListingSearchInput] = None,
        region_hint: Optional[str] = None,
        enrich_mode: Optional[str] = None,
        complex_limit: int = 12,
        expand_articles: bool = False,
        fallback_radius_meters: Optional[List[int]] = None,
        recommend_limit: int = 5,
        history_enrich_limit: int = 3,
    ) -> WorkflowResult:
        try:
            normalized_listing_input = _build_base_listing_input(
                listing_input,
                real_estate_type,
            )
            attempt_radii = _build_attempt_radii(
                radius_meters,
                fallback_radius_meters or [],
            )
            execution_plans = _build_execution_plans(
                attempt_radii,
                normalized_listing_input,
            )

            scan_service = ScanService(self._repository)
            attempts: List[WorkflowAttemptSummary] = []
            aggregated_sources: List[ApiRequestContext] = []
            warnings: List[str] = []
            selected_plan: Optional[WorkflowExecutionPlan] = None
            selected_scan_result: Optional[ScanResult] = None

            for plan in execution_plans:
                scan_result = scan_service.scan_near_queries(
                    near_queries=near_queries,
                    radius_meters=plan.radius_meters,
                    real_estate_type=real_estate_type,
                    listing_input=plan.listing_input,
                    enrich_mode=enrich_mode,
                    complex_limit=complex_limit,
                    expand_articles=expand_articles,
                    region_hint=region_hint,
                )
                aggregated_sources.extend(scan_result.sources)
                warnings.extend(scan_result.warnings)

                attempt_summary = WorkflowAttemptSummary(
                    radius_meters=plan.radius_meters,
                    relaxation_stage=plan.relaxation_stage,
                    completion_status=_resolve_attempt_status(scan_result),
                    item_count=len(scan_result.items),
                    target_count=len(scan_result.targets),
                    failed_target_count=sum(
                        1 for target in scan_result.targets if target.status == "failed"
                    ),
                    warning_count=len(scan_result.warnings),
                    applied_filters=plan.applied_filters,
                    notes=_build_attempt_notes(plan, scan_result),
                )

                if scan_result.items and selected_scan_result is None:
                    selected_plan = plan
                    selected_scan_result = scan_result
                    attempt_summary.selected = True
                    attempts.append(attempt_summary)
                    break

                attempts.append(attempt_summary)

            completion_status = _resolve_workflow_completion_status(
                attempts,
                selected_scan_result,
            )
            final_radius_meters = (
                selected_plan.radius_meters
                if selected_plan is not None
                else (execution_plans[-1].radius_meters if execution_plans else radius_meters)
            )

            recommended_items: List[WorkflowRecommendedItem] = []
            if selected_scan_result is not None:
                (
                    recommended_items,
                    history_sources,
                    history_warnings,
                ) = _build_recommended_items(
                    repository=self._repository,
                    items=selected_scan_result.items,
                    recommend_limit=recommend_limit,
                    history_enrich_limit=history_enrich_limit,
                )
                aggregated_sources.extend(history_sources)
                warnings.extend(history_warnings)

            return WorkflowResult(
                request=WorkflowRequest(
                    near_queries=near_queries,
                    region_hint=region_hint,
                    real_estate_type=real_estate_type,
                    radius_meters=radius_meters,
                    fallback_radius_meters=attempt_radii[1:],
                    complex_limit=complex_limit,
                    expand_articles=expand_articles,
                    history_enrich_limit=history_enrich_limit,
                    listing_input=normalized_listing_input,
                ),
                completion_status=completion_status,
                attempts=attempts,
                final_radius_meters=final_radius_meters,
                selected_reason=_build_selection_reason(
                    selected_plan,
                    initial_radius_meters=radius_meters,
                ),
                scan_result=selected_scan_result,
                recommended_items=recommended_items,
                warnings=_deduplicate_texts(warnings),
                next_actions=_build_next_actions(
                    completion_status=completion_status,
                    listing_input=normalized_listing_input,
                    has_region_hint=bool(region_hint),
                ),
                sources=_deduplicate_sources(aggregated_sources),
            )
        except ServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - 서비스 공통 포맷으로 변환한다.
            raise build_service_error(
                exc,
                error_code="WORKFLOW_FAILED",
                message="에이전트 워크플로우 실행에 실패했습니다.",
                details={
                    "near_queries": near_queries,
                    "radius_meters": radius_meters,
                    "fallback_radius_meters": fallback_radius_meters or [],
                },
            ) from exc


def _build_base_listing_input(
    listing_input: Optional[ListingSearchInput],
    real_estate_type: str,
) -> ListingSearchInput:
    if listing_input is None:
        return ListingSearchInput(real_estate_type=real_estate_type)
    return listing_input.model_copy(
        update={"real_estate_type": listing_input.real_estate_type or real_estate_type}
    )


def _build_attempt_radii(
    initial_radius_meters: int,
    fallback_radius_meters: Sequence[int],
) -> List[int]:
    ordered_radii: List[int] = []
    seen_radii = set()
    for radius_meters in [initial_radius_meters, *fallback_radius_meters]:
        if radius_meters in seen_radii:
            continue
        seen_radii.add(radius_meters)
        ordered_radii.append(radius_meters)
    return ordered_radii or [initial_radius_meters]


def _build_execution_plans(
    attempt_radii: Sequence[int],
    base_listing_input: ListingSearchInput,
) -> List[WorkflowExecutionPlan]:
    plans: List[WorkflowExecutionPlan] = []

    for index, radius_meters in enumerate(attempt_radii):
        relaxation_stage = "initial" if index == 0 else "radius_relaxed"
        plans.append(
            WorkflowExecutionPlan(
                radius_meters=radius_meters,
                listing_input=base_listing_input,
                relaxation_stage=relaxation_stage,
                applied_filters=_describe_listing_filters(base_listing_input, radius_meters),
            )
        )

    current_listing_input = base_listing_input
    final_radius_meters = attempt_radii[-1] if attempt_radii else 500

    price_relaxed_input = _expand_listing_input_price(current_listing_input)
    if price_relaxed_input is not None:
        current_listing_input = price_relaxed_input
        plans.append(
            WorkflowExecutionPlan(
                radius_meters=final_radius_meters,
                listing_input=current_listing_input,
                relaxation_stage="price_relaxed",
                applied_filters=_describe_listing_filters(
                    current_listing_input,
                    final_radius_meters,
                ),
            )
        )

    area_relaxed_input = _expand_listing_input_area(current_listing_input, "area_range")
    if area_relaxed_input is not None:
        current_listing_input = area_relaxed_input
        plans.append(
            WorkflowExecutionPlan(
                radius_meters=final_radius_meters,
                listing_input=current_listing_input,
                relaxation_stage="supply_area_relaxed",
                applied_filters=_describe_listing_filters(
                    current_listing_input,
                    final_radius_meters,
                ),
            )
        )

    exclusive_area_relaxed_input = _expand_listing_input_area(
        current_listing_input,
        "exclusive_area_range",
    )
    if exclusive_area_relaxed_input is not None:
        current_listing_input = exclusive_area_relaxed_input
        plans.append(
            WorkflowExecutionPlan(
                radius_meters=final_radius_meters,
                listing_input=current_listing_input,
                relaxation_stage="exclusive_area_relaxed",
                applied_filters=_describe_listing_filters(
                    current_listing_input,
                    final_radius_meters,
                ),
            )
        )

    return plans


def _expand_listing_input_price(
    listing_input: ListingSearchInput,
) -> Optional[ListingSearchInput]:
    if listing_input.price_range is None:
        return None

    minimum = normalize_price_to_manwon(listing_input.price_range.minimum)
    maximum = normalize_price_to_manwon(listing_input.price_range.maximum)
    if minimum is None and maximum is None:
        return None

    expanded_minimum = max(0, minimum - PRICE_RELAXATION_DELTA_MANWON) if minimum is not None else None
    expanded_maximum = maximum + PRICE_RELAXATION_DELTA_MANWON if maximum is not None else None

    if expanded_minimum == minimum and expanded_maximum == maximum:
        return None

    return listing_input.model_copy(
        update={
            "price_range": PriceRange(
                minimum=expanded_minimum,
                maximum=expanded_maximum,
            )
        }
    )


def _expand_listing_input_area(
    listing_input: ListingSearchInput,
    range_field_name: str,
) -> Optional[ListingSearchInput]:
    area_range = getattr(listing_input, range_field_name)
    if area_range is None:
        return None

    minimum, maximum = resolve_area_range_bounds(
        area_range.minimum,
        area_range.maximum,
    )
    if minimum is None and maximum is None:
        return None

    expanded_minimum = (
        round(max(0.0, minimum - AREA_RELAXATION_DELTA_SQUARE_METER), 2)
        if minimum is not None
        else None
    )
    expanded_maximum = (
        round(maximum + AREA_RELAXATION_DELTA_SQUARE_METER, 2)
        if maximum is not None
        else None
    )

    if expanded_minimum == minimum and expanded_maximum == maximum:
        return None

    return listing_input.model_copy(
        update={
            range_field_name: AreaRange(
                minimum=expanded_minimum,
                maximum=expanded_maximum,
            )
        }
    )


def _resolve_attempt_status(scan_result: ScanResult) -> str:
    if scan_result.items:
        return "success"

    target_statuses = {target.status for target in scan_result.targets if target.status}
    if target_statuses and target_statuses == {"failed"}:
        return "failed"
    if "failed" in target_statuses or "partial" in target_statuses:
        return "partial"
    return "no_results"


def _resolve_workflow_completion_status(
    attempts: Sequence[WorkflowAttemptSummary],
    selected_scan_result: Optional[ScanResult],
) -> str:
    if selected_scan_result is not None and selected_scan_result.items:
        return "success"
    if attempts and all(attempt.completion_status == "failed" for attempt in attempts):
        return "failed"
    if any(attempt.completion_status == "partial" for attempt in attempts):
        return "partial"
    return "no_results"


def _build_attempt_notes(
    plan: WorkflowExecutionPlan,
    scan_result: ScanResult,
) -> List[str]:
    notes: List[str] = []
    stage_note = _format_relaxation_note(plan.relaxation_stage)
    if stage_note:
        notes.append(stage_note)
    if scan_result.filter_stats is not None:
        notes.append(
            "필터 결과 {before}건 -> {after}건".format(
                before=scan_result.filter_stats.before_count,
                after=scan_result.filter_stats.after_count,
            )
        )
    if scan_result.warnings:
        notes.append(f"경고 {len(scan_result.warnings)}건")
    return notes


def _format_relaxation_note(relaxation_stage: str) -> Optional[str]:
    note_by_stage = {
        "initial": "초기 조건으로 조회했습니다.",
        "radius_relaxed": "반경 조건을 완화했습니다.",
        "price_relaxed": "가격 범위를 ±5000만원 확장했습니다.",
        "supply_area_relaxed": "공급면적 조건을 약 ±5평 범위로 확장했습니다.",
        "exclusive_area_relaxed": "전용면적 조건을 약 ±5평 범위로 확장했습니다.",
    }
    return note_by_stage.get(relaxation_stage)


def _build_selection_reason(
    selected_plan: Optional[WorkflowExecutionPlan],
    initial_radius_meters: int,
) -> Optional[str]:
    if selected_plan is None:
        return None
    if selected_plan.relaxation_stage == "initial":
        return "초기 조건에서 바로 결과를 확보했습니다."
    if selected_plan.relaxation_stage == "radius_relaxed":
        return (
            f"초기 반경에서 결과가 없어 {selected_plan.radius_meters}m까지 반경을 완화했습니다."
        )
    if selected_plan.relaxation_stage == "price_relaxed":
        if selected_plan.radius_meters == initial_radius_meters:
            return "현재 반경에서 결과가 없어 가격 범위를 확장했습니다."
        return (
            f"반경 {initial_radius_meters}m~{selected_plan.radius_meters}m에서 결과가 없어 가격 범위를 확장했습니다."
        )
    if selected_plan.relaxation_stage == "supply_area_relaxed":
        return "반경/가격 완화 후에도 결과가 없어 공급면적 조건을 넓혔습니다."
    if selected_plan.relaxation_stage == "exclusive_area_relaxed":
        return "반경/가격/공급면적 완화 후에도 결과가 없어 전용면적 조건을 넓혔습니다."
    return None


def _build_recommended_items(
    repository: NaverLandRepository,
    items: Sequence[NormalizedArticle],
    recommend_limit: int,
    history_enrich_limit: int,
) -> Tuple[List[WorkflowRecommendedItem], List[ApiRequestContext], List[str]]:
    ranked_items = _rank_articles_for_recommendation(items)
    selected_items = list(ranked_items[: max(recommend_limit, history_enrich_limit)])
    history_sources: List[ApiRequestContext] = []
    warnings: List[str] = []
    recommended_items: List[WorkflowRecommendedItem] = []
    history_service = HistoryService(repository)

    for index, item in enumerate(selected_items, start=1):
        premium_summary: Optional[PremiumSummary] = None
        if index <= history_enrich_limit and item.article_no:
            try:
                history_result = history_service.create_history(
                    HistoryInput(article_no=item.article_no)
                )
                premium_summary = history_result.premium_summary
                history_sources.extend(history_result.sources)
            except ServiceError as exc:
                warnings.append(
                    f"{item.article_name or item.article_no}: history {exc.error_code}"
                )

        recommended_items.append(
            WorkflowRecommendedItem(
                **item.model_dump(exclude_none=True),
                rank=index,
                premium_summary=premium_summary,
            )
        )

    sorted_recommended_items = sorted(
        recommended_items,
        key=lambda item: (
            item.distance_meters if item.distance_meters is not None else 999999,
            item.premium_summary.premium_rate
            if item.premium_summary and item.premium_summary.premium_rate is not None
            else 999999,
            item.price if item.price is not None else 999999,
        ),
    )[:recommend_limit]

    reranked_items: List[WorkflowRecommendedItem] = []
    for rank, item in enumerate(sorted_recommended_items, start=1):
        reranked_items.append(item.model_copy(update={"rank": rank}))

    return reranked_items, history_sources, warnings


def _rank_articles_for_recommendation(
    items: Sequence[NormalizedArticle],
) -> List[NormalizedArticle]:
    return sorted(
        items,
        key=lambda item: (
            item.distance_meters if item.distance_meters is not None else 999999,
            item.price if item.price is not None else 999999,
            item.article_no or item.article_name or "",
        ),
    )


def _build_next_actions(
    completion_status: str,
    listing_input: ListingSearchInput,
    has_region_hint: bool,
) -> List[str]:
    if completion_status == "success":
        return [
            "추천 후보에 대해 history 또는 compare로 실거래 대비 수준을 추가 검증합니다.",
        ]

    next_actions = ["반경을 1500m 이상으로 넓혀 재시도합니다."]
    if listing_input.price_range is not None:
        next_actions.append("가격 범위를 추가로 넓혀 재시도합니다.")
    if listing_input.area_range is not None:
        next_actions.append("공급면적 조건을 더 완화합니다.")
    if listing_input.exclusive_area_range is not None:
        next_actions.append("전용면적 조건을 더 완화합니다.")
    if not has_region_hint:
        next_actions.append("동명이역 가능성이 있으면 --region-hint를 추가합니다.")
    return _deduplicate_texts(next_actions)


def _describe_listing_filters(
    listing_input: ListingSearchInput,
    radius_meters: int,
) -> List[str]:
    filters = [f"반경 {radius_meters}m"]
    if listing_input.price_range is not None:
        filters.append(
            "가격 {minimum}~{maximum}만원".format(
                minimum=_format_bound(listing_input.price_range.minimum),
                maximum=_format_bound(listing_input.price_range.maximum),
            )
        )
    if listing_input.area_range is not None:
        filters.append(
            "공급면적 {minimum}~{maximum}㎡".format(
                minimum=_format_bound(listing_input.area_range.minimum),
                maximum=_format_bound(listing_input.area_range.maximum),
            )
        )
    if listing_input.exclusive_area_range is not None:
        filters.append(
            "전용면적 {minimum}~{maximum}㎡".format(
                minimum=_format_bound(listing_input.exclusive_area_range.minimum),
                maximum=_format_bound(listing_input.exclusive_area_range.maximum),
            )
        )
    return filters


def _format_bound(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)



def _deduplicate_sources(
    sources: Sequence[ApiRequestContext],
) -> List[ApiRequestContext]:
    unique_sources: List[ApiRequestContext] = []
    seen_keys = set()
    for source in sources:
        key = (source.endpoint, str(source.params), source.http_status)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_sources.append(source)
    return unique_sources


def _deduplicate_texts(values: Sequence[str]) -> List[str]:
    unique_values: List[str] = []
    seen_values = set()
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen_values:
            continue
        seen_values.add(normalized)
        unique_values.append(normalized)
    return unique_values
