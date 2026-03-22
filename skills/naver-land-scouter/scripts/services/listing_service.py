from __future__ import annotations

from typing import Any, List

from ..normalization import normalize_price_to_manwon
from ..param_builder import build_article_list_params
from ..schemas import ListingResult, ListingSearchInput, NormalizedArticle, RawArticleSummary
from .contracts import NaverLandRepository
from .errors import ServiceError, build_service_error


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
            normalized_items = [
                _normalize_article_summary(item) for item in raw_items
            ]
            return ListingResult(
                query_text=listing_input.query_text,
                items=normalized_items,
                sources=[context],
            )
        except Exception as exc:  # noqa: BLE001 - 서비스 레이어에서 공통 포맷으로 변환한다.
            raise build_service_error(
                exc,
                error_code="LISTING_SEARCH_FAILED",
                message="매물 검색에 실패했습니다.",
                details={"complex_no": complex_no},
            ) from exc


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


def _normalize_article_summary(raw: dict) -> NormalizedArticle:
    parsed = RawArticleSummary.model_validate(raw)
    return NormalizedArticle(
        article_no=parsed.article_no,
        complex_no=parsed.complex_no,
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
        article_feature_description=parsed.article_feature_description,
    )
