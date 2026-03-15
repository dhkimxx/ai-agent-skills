from __future__ import annotations

from typing import List, Optional, Tuple

from ..normalization import normalize_area_to_square_meter, normalize_price_to_manwon
from ..schemas import (
    ComparisonItem,
    ComparisonResult,
    NormalizedArticle,
    RawArticleDetail,
)
from .contracts import NaverLandRepository
from .errors import ServiceError


class ComparisonService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def compare_articles(self, article_nos: List[str]) -> ComparisonResult:
        if not article_nos:
            raise ServiceError(
                error_code="COMPARISON_INPUT_EMPTY",
                message="비교할 매물 ID가 없습니다.",
            )

        try:
            sources = []
            article_metrics: List[Tuple[NormalizedArticle, Optional[float]]] = []

            for article_no in article_nos:
                payload, context = self._repository.fetch_article_detail(article_no)
                sources.append(context)
                article = _normalize_article_detail(payload)
                price_per_area = _calculate_price_per_area(article)
                article_metrics.append((article, price_per_area))

            best_value = _find_best_price_per_area(article_metrics)
            items = [
                ComparisonItem(
                    article=article,
                    score=_calculate_relative_score(price_per_area, best_value),
                    score_reason=_build_score_reason(price_per_area),
                )
                for article, price_per_area in article_metrics
            ]

            recommendation = _build_recommendation(items)

            return ComparisonResult(
                items=items,
                recommendation=recommendation,
                sources=sources,
            )
        except Exception as exc:  # noqa: BLE001 - 서비스 공통 에러로 변환한다.
            raise ServiceError(
                error_code="COMPARISON_FAILED",
                message="매물 비교에 실패했습니다.",
                details={"article_nos": article_nos},
            ) from exc


def _normalize_article_detail(payload: dict) -> NormalizedArticle:
    parsed = RawArticleDetail.model_validate(payload)
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


def _calculate_price_per_area(article: NormalizedArticle) -> Optional[float]:
    price = article.price
    area = normalize_area_to_square_meter(article.exclusive_area or article.area)
    if price is None or area is None or area == 0:
        return None
    return round(price / area, 4)


def _calculate_relative_score(
    price_per_area: Optional[float],
    best_value: Optional[float],
) -> Optional[float]:
    if price_per_area is None:
        return None
    if best_value is None or best_value <= 0:
        return None
    # 단순 비교 지표로 낮을수록 높은 점수가 되게 변환한다.
    return round(best_value / price_per_area, 3)


def _find_best_price_per_area(
    article_metrics: List[Tuple[NormalizedArticle, Optional[float]]]
) -> Optional[float]:
    values = [value for _, value in article_metrics if value is not None]
    if not values:
        return None
    return min(values)


def _build_score_reason(price_per_area: Optional[float]) -> Optional[str]:
    if price_per_area is None:
        return "가격 또는 면적 정보가 부족해 비교 점수를 계산하지 못했습니다."
    return f"면적 대비 가격(만원/㎡): {price_per_area} (낮을수록 유리)"


def _build_recommendation(items: List[ComparisonItem]) -> Optional[str]:
    scored_items = [item for item in items if item.score is not None]
    if not scored_items:
        return "비교 점수를 계산할 수 있는 매물이 없습니다."
    best_item = max(scored_items, key=lambda item: item.score or 0)
    name = best_item.article.article_name or best_item.article.article_no
    return f"가격/면적 기준으로 {name}이(가) 가장 유리합니다."
