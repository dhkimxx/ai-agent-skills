from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ..location_utils import (
    build_bounding_box_from_radius,
    parse_map_search_deep_link,
)
from ..schemas import (
    ApiRequestContext,
    NormalizedComplex,
    RawSearchComplex,
    RawSearchRegion,
    ResolvedLocation,
    SearchResult,
)
from .contracts import NaverLandRepository
from .discovery_service import DiscoveryService
from .errors import ServiceError, build_service_error


@dataclass(frozen=True)
class LocationResolutionDecision:
    query_intent: str
    candidates: List[ResolvedLocation]
    preferred_candidate: Optional[ResolvedLocation]
    ambiguity_reason: Optional[str]
    region_hint: Optional[str] = None
    resolution_strategy: str = "direct"
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchQueryProfile:
    original_query: str
    core_query: str
    query_intent: str
    region_hint: Optional[str]


@dataclass(frozen=True)
class LocationResolutionBundle:
    profile: SearchQueryProfile
    decision: LocationResolutionDecision
    complexes: List[NormalizedComplex]
    sources: List[ApiRequestContext]


class LocationService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def search(
        self,
        query_text: str,
        radius_meters: int = 700,
        real_estate_type: str = "APT",
        enrich_mode: Optional[str] = None,
        region_hint: Optional[str] = None,
    ) -> SearchResult:
        try:
            bundle = self.resolve_location_bundle(query_text, region_hint=region_hint)
            decision = bundle.decision
            complexes = bundle.complexes
            if (
                decision.preferred_candidate is None
                and decision.query_intent == "station"
            ):
                complexes = []

            nearby_complexes = []
            if decision.preferred_candidate:
                candidate = decision.preferred_candidate
                try:
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
                except Exception:
                    nearby_complexes = []

            return SearchResult(
                query_text=query_text,
                query_intent=decision.query_intent,
                region_hint=decision.region_hint,
                resolution_strategy=decision.resolution_strategy,
                candidates=decision.candidates,
                preferred_candidate=decision.preferred_candidate,
                alternatives=_build_alternatives(
                    decision.candidates,
                    decision.preferred_candidate,
                ),
                ambiguity_reason=decision.ambiguity_reason,
                warnings=decision.warnings,
                complexes=complexes,
                nearby_complexes=nearby_complexes,
                sources=bundle.sources,
            )
        except ServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - 검색 단계도 공통 에러 포맷으로 변환한다.
            raise build_service_error(
                exc,
                error_code="LOCATION_SEARCH_FAILED",
                message="위치 검색에 실패했습니다.",
                details={"query_text": query_text, "region_hint": region_hint},
            ) from exc

    def resolve_location_bundle(
        self,
        query_text: str,
        region_hint: Optional[str] = None,
    ) -> LocationResolutionBundle:
        profile = _build_search_query_profile(query_text, region_hint)
        payload, context = self._repository.fetch_search(
            {"keyword": profile.original_query, "page": 1}
        )
        decision = _build_location_resolution(
            profile.original_query,
            payload,
            query_intent=profile.query_intent,
            region_hint=profile.region_hint,
        )
        complexes = _extract_search_complexes(payload)
        sources = [context]

        if _should_use_region_hint_fallback(profile, decision):
            fallback_bundle = _build_region_hint_fallback_bundle(
                self._repository,
                profile,
            )
            if fallback_bundle is not None:
                decision = fallback_bundle.decision
                if fallback_bundle.complexes:
                    complexes = fallback_bundle.complexes
                sources.extend(fallback_bundle.sources)

        return LocationResolutionBundle(
            profile=profile,
            decision=decision,
            complexes=complexes,
            sources=sources,
        )

    def resolve_single_location(
        self,
        query_text: str,
        region_hint: Optional[str] = None,
    ) -> ResolvedLocation:
        bundle = self.resolve_location_bundle(query_text, region_hint=region_hint)
        decision = bundle.decision
        if not decision.candidates:
            raise ServiceError(
                error_code="LOCATION_NOT_FOUND",
                message="검색어에 해당하는 위치를 찾지 못했습니다.",
                details={
                    "query_text": query_text,
                    "region_hint": decision.region_hint,
                    "resolution_strategy": decision.resolution_strategy,
                },
            )
        if decision.preferred_candidate is None:
            raise ServiceError(
                error_code="LOCATION_AMBIGUOUS",
                message="검색어가 여러 위치로 해석됩니다. 더 구체적으로 입력하세요.",
                details={
                    "query_text": query_text,
                    "query_intent": decision.query_intent,
                    "region_hint": decision.region_hint,
                    "ambiguity_reason": decision.ambiguity_reason,
                    "resolution_strategy": decision.resolution_strategy,
                    "warnings": decision.warnings,
                    "candidates": [
                        candidate.model_dump(by_alias=True, exclude_none=True)
                        for candidate in decision.candidates
                    ],
                    "sources": [
                        source.model_dump(by_alias=True, exclude_none=True)
                        for source in bundle.sources
                    ],
                },
            )
        return decision.preferred_candidate


def _build_location_resolution(
    query_text: str,
    payload: Any,
    query_intent: Optional[str] = None,
    region_hint: Optional[str] = None,
) -> LocationResolutionDecision:
    resolved_query_intent = query_intent or _infer_query_intent(query_text)
    candidates = _extract_location_candidates(query_text, payload, resolved_query_intent)
    candidates = _score_candidates(candidates, query_text, resolved_query_intent)
    preferred_candidate, ambiguity_reason = _choose_preferred_candidate(
        candidates,
        resolved_query_intent,
    )
    return LocationResolutionDecision(
        query_intent=resolved_query_intent,
        candidates=candidates,
        preferred_candidate=preferred_candidate,
        ambiguity_reason=ambiguity_reason,
        region_hint=region_hint,
    )


def _extract_location_candidates(
    query_text: str,
    payload: Any,
    query_intent: str,
) -> List[ResolvedLocation]:
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
                location_type="region",
            )
        )

    deep_link = payload.get("deepLink")
    latitude, longitude, zoom = parse_map_search_deep_link(deep_link)
    if latitude is not None and longitude is not None:
        candidates.append(
            ResolvedLocation(
                query_text=query_text,
                label=query_text,
                latitude=latitude,
                longitude=longitude,
                zoom=zoom or 16,
                deep_link=deep_link,
                match_type="landmark",
                location_type="station" if query_text.strip().endswith("역") else "landmark",
            )
        )

    complexes = _extract_search_complexes(payload)
    if query_intent == "complex":
        for complex_item in complexes[:5]:
            if complex_item.latitude is None or complex_item.longitude is None:
                continue
            candidates.append(
                ResolvedLocation(
                    query_text=query_text,
                    label=complex_item.complex_name or query_text,
                    latitude=complex_item.latitude,
                    longitude=complex_item.longitude,
                    zoom=16,
                    address=complex_item.address,
                    match_type="complex",
                    location_type="complex",
                )
            )
    elif not candidates and len(complexes) == 1:
        complex_item = complexes[0]
        if complex_item.latitude is not None and complex_item.longitude is not None:
            candidates.append(
                ResolvedLocation(
                    query_text=query_text,
                    label=complex_item.complex_name or query_text,
                    latitude=complex_item.latitude,
                    longitude=complex_item.longitude,
                    zoom=16,
                    address=complex_item.address,
                    match_type="complex",
                    location_type="complex",
                )
            )

    return _deduplicate_candidates(candidates)


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


def _deduplicate_complexes(complexes: List[NormalizedComplex]) -> List[NormalizedComplex]:
    unique_complexes: List[NormalizedComplex] = []
    seen_keys = set()
    for complex_item in complexes:
        key = (
            complex_item.complex_no,
            round(complex_item.latitude or 0, 6),
            round(complex_item.longitude or 0, 6),
            complex_item.complex_name,
        )
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique_complexes.append(complex_item)
    return unique_complexes


def _infer_query_intent(query_text: str) -> str:
    normalized = query_text.strip()
    if normalized.endswith("역"):
        return "station"
    if normalized.endswith(("동", "읍", "면", "리", "가", "구", "시", "군")):
        return "region"
    if any(token in normalized for token in ("아파트", "단지")):
        return "complex"
    return "unknown"


def _build_search_query_profile(
    query_text: str,
    explicit_region_hint: Optional[str],
) -> SearchQueryProfile:
    normalized_query = " ".join(query_text.strip().split())
    query_intent = _infer_query_intent(normalized_query)
    tokens = normalized_query.split()
    core_query = normalized_query
    implicit_region_hint = None

    if query_intent == "station" and len(tokens) >= 2 and tokens[-1].endswith("역"):
        core_query = tokens[-1]
        implicit_region_hint = " ".join(tokens[:-1])

    resolved_region_hint = _normalize_hint_text(explicit_region_hint or implicit_region_hint)

    return SearchQueryProfile(
        original_query=normalized_query,
        core_query=core_query,
        query_intent=query_intent,
        region_hint=resolved_region_hint,
    )


def _score_candidates(
    candidates: List[ResolvedLocation],
    query_text: str,
    query_intent: str,
) -> List[ResolvedLocation]:
    scored_candidates: List[ResolvedLocation] = []
    for candidate in candidates:
        score = _calculate_candidate_score(candidate, query_text, query_intent)
        scored_candidates.append(candidate.model_copy(update={"score": score}))
    return sorted(
        scored_candidates,
        key=lambda candidate: (
            candidate.score if candidate.score is not None else -1,
            candidate.label or "",
        ),
        reverse=True,
    )


def _calculate_candidate_score(
    candidate: ResolvedLocation,
    query_text: str,
    query_intent: str,
) -> int:
    score = 0
    location_type = candidate.location_type or "unknown"
    label = candidate.label or ""
    address = candidate.address or ""
    normalized_query = query_text.strip()

    if location_type == query_intent:
        score += 100
    elif query_intent == "unknown":
        score += 40
    elif location_type == "complex" and query_intent == "region":
        score += 10

    if label == normalized_query:
        score += 30
    elif label.endswith(normalized_query):
        score += 20
    elif normalized_query and normalized_query in label:
        score += 10

    if address.endswith(normalized_query):
        score += 10

    if location_type == "station" and normalized_query.endswith("역"):
        score += 10

    return score


def _score_region_hint_candidates(
    candidates: List[ResolvedLocation],
    original_query_text: str,
    region_hint: str,
    place_hint: Optional[str],
) -> List[ResolvedLocation]:
    region_tokens = _split_hint_tokens(region_hint)
    place_tokens = _split_hint_tokens(place_hint)
    scored_candidates: List[ResolvedLocation] = []

    for candidate in candidates:
        label_text = " ".join(
            part for part in [candidate.label, candidate.address] if part
        )
        score = 0

        if candidate.location_type == "region":
            score += 50

        matched_region_tokens = sum(
            1 for token in region_tokens if token and token in label_text
        )
        matched_place_tokens = sum(
            1 for token in place_tokens if token and token in label_text
        )

        score += matched_region_tokens * 25
        score += matched_place_tokens * 20

        if region_tokens and matched_region_tokens == len(region_tokens):
            score += 20
        if place_tokens and matched_place_tokens == len(place_tokens):
            score += 20

        scored_candidates.append(
            candidate.model_copy(
                update={
                    "query_text": original_query_text,
                    "score": score,
                }
            )
        )

    return sorted(
        scored_candidates,
        key=lambda candidate: (
            candidate.score if candidate.score is not None else -1,
            candidate.label or "",
        ),
        reverse=True,
    )


def _choose_preferred_candidate(
    candidates: List[ResolvedLocation],
    query_intent: str,
) -> tuple[Optional[ResolvedLocation], Optional[str]]:
    if not candidates:
        return None, None

    typed_candidates = [
        candidate
        for candidate in candidates
        if candidate.location_type == query_intent
    ]
    if query_intent == "station" and not typed_candidates:
        return None, "역 질의인데 역 후보를 찾지 못했습니다. 지역 힌트를 추가하세요."
    if query_intent in {"station", "region", "complex"} and typed_candidates:
        candidates = typed_candidates

    if len(candidates) == 1:
        return candidates[0], None

    top_candidate = candidates[0]
    second_candidate = candidates[1]
    top_score = top_candidate.score or 0
    second_score = second_candidate.score or 0

    if query_intent != "unknown" and top_score >= second_score + 15:
        return top_candidate, None

    if top_score == second_score:
        return None, "동일하거나 유사한 우선순위의 위치 후보가 여러 개입니다."

    return None, "질의만으로는 단일 위치를 확정하기에 정보가 부족합니다."


def _build_region_hint_fallback_bundle(
    repository: NaverLandRepository,
    profile: SearchQueryProfile,
) -> Optional[LocationResolutionBundle]:
    if not profile.region_hint:
        return None

    fallback_candidates: List[ResolvedLocation] = []
    fallback_complexes: List[NormalizedComplex] = []
    fallback_sources: List[ApiRequestContext] = []

    for keyword in _build_region_hint_queries(profile):
        payload, context = repository.fetch_search({"keyword": keyword, "page": 1})
        fallback_sources.append(context)
        fallback_complexes.extend(_extract_search_complexes(payload))
        fallback_candidates.extend(
            candidate
            for candidate in _extract_location_candidates(keyword, payload, "region")
            if candidate.location_type == "region"
        )

    deduplicated_candidates = _deduplicate_candidates(fallback_candidates)
    if not deduplicated_candidates:
        return LocationResolutionBundle(
            profile=profile,
            decision=LocationResolutionDecision(
                query_intent=profile.query_intent,
                candidates=[],
                preferred_candidate=None,
                ambiguity_reason="지역 힌트로도 위치를 좁히지 못했습니다.",
                region_hint=profile.region_hint,
                resolution_strategy="region_hint_unresolved",
                warnings=["지역 힌트를 적용했지만 후보를 찾지 못했습니다."],
            ),
            complexes=[],
            sources=fallback_sources,
        )

    scored_candidates = _score_region_hint_candidates(
        deduplicated_candidates,
        original_query_text=profile.original_query,
        region_hint=profile.region_hint,
        place_hint=_derive_place_hint(profile.core_query),
    )
    preferred_candidate, ambiguity_reason = _choose_region_hint_candidate(
        scored_candidates
    )

    warnings: List[str] = []
    resolution_strategy = "region_hint_unresolved"
    if preferred_candidate is not None:
        warnings.append("역 후보를 찾지 못해 지역 힌트 기반 중심점으로 대체했습니다.")
        resolution_strategy = "region_hint_region_center"

    return LocationResolutionBundle(
        profile=profile,
        decision=LocationResolutionDecision(
            query_intent=profile.query_intent,
            candidates=scored_candidates,
            preferred_candidate=preferred_candidate,
            ambiguity_reason=ambiguity_reason,
            region_hint=profile.region_hint,
            resolution_strategy=resolution_strategy,
            warnings=warnings,
        ),
        complexes=_deduplicate_complexes(fallback_complexes),
        sources=fallback_sources,
    )


def _build_region_hint_queries(profile: SearchQueryProfile) -> List[str]:
    place_hint = _derive_place_hint(profile.core_query)
    raw_queries = [
        f"{profile.region_hint} {profile.core_query}" if profile.region_hint else None,
        f"{profile.region_hint} {place_hint}"
        if profile.region_hint and place_hint
        else None,
        profile.region_hint,
    ]
    unique_queries: List[str] = []
    seen_queries = set()
    for query_text in raw_queries:
        normalized_query = _normalize_hint_text(query_text)
        if not normalized_query or normalized_query in seen_queries:
            continue
        seen_queries.add(normalized_query)
        unique_queries.append(normalized_query)
    return unique_queries


def _should_use_region_hint_fallback(
    profile: SearchQueryProfile,
    decision: LocationResolutionDecision,
) -> bool:
    if profile.query_intent != "station" or not profile.region_hint:
        return False
    if any(candidate.location_type == "station" for candidate in decision.candidates):
        return False
    return True


def _choose_region_hint_candidate(
    candidates: List[ResolvedLocation],
) -> tuple[Optional[ResolvedLocation], Optional[str]]:
    if not candidates:
        return None, "지역 힌트와 일치하는 후보를 찾지 못했습니다."
    if len(candidates) == 1:
        return candidates[0], None

    top_candidate = candidates[0]
    second_candidate = candidates[1]
    top_score = top_candidate.score or 0
    second_score = second_candidate.score or 0

    if top_score >= second_score + 20:
        return top_candidate, None
    if top_score == second_score:
        return None, "지역 힌트와 일치하는 후보가 여러 개입니다."
    return None, "지역 힌트만으로는 단일 위치를 확정하기에 정보가 부족합니다."


def _derive_place_hint(query_text: str) -> Optional[str]:
    normalized_query = query_text.strip()
    if normalized_query.endswith("역"):
        normalized_query = normalized_query[:-1]
    normalized_query = normalized_query.strip()
    return normalized_query or None


def _normalize_hint_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    normalized = " ".join(text.strip().split())
    return normalized or None


def _split_hint_tokens(text: Optional[str]) -> List[str]:
    if not text:
        return []
    return [token for token in text.split() if token]


def _build_alternatives(
    candidates: List[ResolvedLocation],
    preferred_candidate: Optional[ResolvedLocation],
) -> List[ResolvedLocation]:
    if preferred_candidate is None:
        return candidates
    return [
        candidate
        for candidate in candidates
        if not (
            candidate.latitude == preferred_candidate.latitude
            and candidate.longitude == preferred_candidate.longitude
            and candidate.label == preferred_candidate.label
        )
    ]
