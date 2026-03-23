from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from statistics import median
from typing import Any, List, Optional

from ..normalization import normalize_price_to_manwon
from ..param_builder import build_complex_price_params
from ..schemas import (
    ComplexAnalysisInput,
    HistoryInput,
    HistoryResult,
    HistoryTradePoint,
    HistoryWindowSummary,
    NormalizedArticle,
    PremiumSummary,
    RawArticleDetail,
)
from .article_payload import flatten_article_payload
from .contracts import NaverLandRepository
from .errors import ServiceError, build_service_error

PRIMARY_WINDOW_YEARS = 1
SECONDARY_WINDOW_YEARS = [3, 10]
PREMIUM_RATE_THRESHOLD = 5.0


@dataclass(frozen=True)
class TradeSample:
    trade_date: date
    price: int
    floor: Optional[str] = None


class HistoryService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def create_history(self, history_input: HistoryInput) -> HistoryResult:
        if not history_input.article_no and not history_input.complex_no:
            raise ServiceError(
                error_code="HISTORY_INPUT_INVALID",
                message="history 조회에는 article_no 또는 complex_no가 필요합니다.",
            )

        sources = []
        article: Optional[NormalizedArticle] = None
        complex_no = history_input.complex_no
        trade_type = history_input.trade_type or "A1"
        area_no = history_input.area_no

        try:
            if history_input.article_no:
                article_payload, article_context = self._repository.fetch_article_detail(
                    history_input.article_no
                )
                sources.append(article_context)
                article, complex_no, trade_type, area_no = _resolve_article_context(
                    article_payload,
                    history_input,
                )

            if not complex_no:
                raise ServiceError(
                    error_code="HISTORY_COMPLEX_NOT_FOUND",
                    message="history 조회에 필요한 complex_no를 확인할 수 없습니다.",
                )

            year_window = max([PRIMARY_WINDOW_YEARS, *SECONDARY_WINDOW_YEARS])
            # table 엔드포인트는 최근 일부 행만 주는 경우가 있어, 장기 실거래 비교는 chart의 실거래 배열을 기준으로 계산한다.
            chart_params = build_complex_price_params(
                ComplexAnalysisInput(
                    complex_no=complex_no,
                    trade_type=trade_type,
                    area_no=area_no,
                    year=year_window,
                ),
                result_type="chart",
            )
            chart_payload, chart_context = self._repository.fetch_complex_prices(
                complex_no,
                chart_params,
            )
            sources.append(chart_context)

            trade_samples = _extract_trade_samples(chart_payload)
            trade_samples = _limit_trade_samples_to_max_window(trade_samples)
            window_summaries = _build_window_summaries(trade_samples)
            premium_summary = _build_premium_summary(
                article.price if article else None,
                window_summaries,
            )

            return HistoryResult(
                article=article,
                trade_type=trade_type,
                area_no=area_no,
                trade_points=[
                    HistoryTradePoint(
                        trade_date=sample.trade_date.isoformat(),
                        price=sample.price,
                        floor=sample.floor,
                    )
                    for sample in trade_samples
                ],
                window_summaries=window_summaries,
                premium_summary=premium_summary,
                sources=sources,
            )
        except ServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - 서비스 공통 포맷으로 변환한다.
            raise build_service_error(
                exc,
                error_code="HISTORY_BUILD_FAILED",
                message="실거래 히스토리 생성에 실패했습니다.",
                details={
                    "article_no": history_input.article_no,
                    "complex_no": complex_no,
                },
            ) from exc


def _resolve_article_context(
    payload: Any,
    history_input: HistoryInput,
) -> tuple[NormalizedArticle, Optional[str], str, Optional[str]]:
    flattened = flatten_article_payload(payload)
    article_detail = payload.get("articleDetail", {}) if isinstance(payload, dict) else {}
    article_addition = payload.get("articleAddition", {}) if isinstance(payload, dict) else {}
    parsed = RawArticleDetail.model_validate(flattened)
    complex_no = history_input.complex_no or parsed.complex_no or flattened.get("hscpNo")
    trade_type = history_input.trade_type or parsed.trade_type or "A1"
    area_no = history_input.area_no or parsed.area_no or _stringify(flattened.get("ptpNo"))

    article = NormalizedArticle(
        article_no=parsed.article_no,
        complex_no=complex_no,
        article_name=parsed.article_name,
        trade_type=trade_type,
        real_estate_type=parsed.real_estate_type,
        price=normalize_price_to_manwon(parsed.deal_price or parsed.price),
        rent_price=normalize_price_to_manwon(parsed.rent_price),
        area=parsed.area or parsed.supply_area,
        exclusive_area=parsed.exclusive_area,
        supply_area=parsed.supply_area or parsed.area,
        floor_info=parsed.floor_info,
        direction=parsed.direction,
        address=_stringify(
            article_detail.get("exposureAddress")
            or article_detail.get("address")
            or article_detail.get("detailAddress")
            or parsed.address
        ),
        dong_name=_stringify(
            article_detail.get("sectionName")
            or article_addition.get("sectionName")
            or parsed.dong_name
        ),
        latitude=_to_optional_float(
            article_detail.get("latitude")
            or article_addition.get("latitude")
            or parsed.latitude
        ),
        longitude=_to_optional_float(
            article_detail.get("longitude")
            or article_addition.get("longitude")
            or parsed.longitude
        ),
        article_feature_description=parsed.article_feature_description,
    )
    return article, complex_no, trade_type, area_no


def _extract_trade_samples(payload: Any) -> List[TradeSample]:
    if not isinstance(payload, dict):
        return []

    date_values = payload.get("realPriceDataXList")
    price_values = payload.get("realPriceDataYList")
    floor_values = payload.get("floorList") or []

    if not isinstance(date_values, list) or not isinstance(price_values, list):
        return []

    samples: List[TradeSample] = []
    for index in range(1, min(len(date_values), len(price_values))):
        trade_date = _parse_trade_date(date_values[index])
        price = normalize_price_to_manwon(price_values[index])
        if trade_date is None or price is None:
            continue
        floor = None
        floor_index = index - 1
        if floor_index < len(floor_values):
            floor = _stringify(floor_values[floor_index])
        samples.append(
            TradeSample(
                trade_date=trade_date,
                price=price,
                floor=floor,
            )
        )

    samples.sort(key=lambda sample: sample.trade_date, reverse=True)
    return samples


def _build_window_summaries(
    trade_samples: List[TradeSample],
    base_date: Optional[date] = None,
) -> List[HistoryWindowSummary]:
    reference_date = base_date or date.today()
    summaries: List[HistoryWindowSummary] = []

    for years in [PRIMARY_WINDOW_YEARS, *SECONDARY_WINDOW_YEARS]:
        start_date = _subtract_years(reference_date, years)
        filtered = [
            sample
            for sample in trade_samples
            if start_date <= sample.trade_date <= reference_date
        ]
        prices = [sample.price for sample in filtered]
        latest_trade_date = filtered[0].trade_date.isoformat() if filtered else None

        summaries.append(
            HistoryWindowSummary(
                years=years,
                sample_size=len(filtered),
                start_date=start_date.isoformat(),
                end_date=reference_date.isoformat(),
                average_price=_safe_average(prices),
                median_price=_safe_median(prices),
                minimum_price=min(prices) if prices else None,
                maximum_price=max(prices) if prices else None,
                latest_trade_date=latest_trade_date,
            )
        )

    return summaries


def _limit_trade_samples_to_max_window(
    trade_samples: List[TradeSample],
    base_date: Optional[date] = None,
) -> List[TradeSample]:
    reference_date = base_date or date.today()
    start_date = _subtract_years(reference_date, max([PRIMARY_WINDOW_YEARS, *SECONDARY_WINDOW_YEARS]))
    return [
        sample
        for sample in trade_samples
        if start_date <= sample.trade_date <= reference_date
    ]


def _build_premium_summary(
    current_asking_price: Optional[int],
    window_summaries: List[HistoryWindowSummary],
) -> PremiumSummary:
    primary_summary = next(
        (summary for summary in window_summaries if summary.years == PRIMARY_WINDOW_YEARS),
        None,
    )
    if primary_summary is None:
        return PremiumSummary(
            primary_window_years=PRIMARY_WINDOW_YEARS,
            current_asking_price=current_asking_price,
            judgement="unknown",
            judgement_reason="기준 윈도우 요약을 만들지 못했습니다.",
        )

    if current_asking_price is None:
        return PremiumSummary(
            primary_window_years=PRIMARY_WINDOW_YEARS,
            current_asking_price=None,
            reference_trade_average_price=primary_summary.average_price,
            reference_trade_median_price=primary_summary.median_price,
            sample_size=primary_summary.sample_size,
            latest_trade_date=primary_summary.latest_trade_date,
            judgement="unknown",
            judgement_reason="현재 매물 호가가 없어 Premium/Discount를 계산할 수 없습니다.",
        )

    if primary_summary.average_price is None or primary_summary.sample_size == 0:
        return PremiumSummary(
            primary_window_years=PRIMARY_WINDOW_YEARS,
            current_asking_price=current_asking_price,
            sample_size=0,
            judgement="unknown",
            judgement_reason="최근 1년 실거래 표본이 없어 비교할 수 없습니다.",
        )

    premium_amount = current_asking_price - primary_summary.average_price
    premium_rate = round((premium_amount / primary_summary.average_price) * 100, 2)

    if premium_rate >= PREMIUM_RATE_THRESHOLD:
        judgement = "premium"
        reason = "현재 호가가 최근 1년 평균 실거래가보다 유의하게 높습니다."
    elif premium_rate <= -PREMIUM_RATE_THRESHOLD:
        judgement = "discount"
        reason = "현재 호가가 최근 1년 평균 실거래가보다 유의하게 낮습니다."
    else:
        judgement = "fair"
        reason = "현재 호가가 최근 1년 평균 실거래가와 큰 차이가 없습니다."

    return PremiumSummary(
        primary_window_years=PRIMARY_WINDOW_YEARS,
        current_asking_price=current_asking_price,
        reference_trade_average_price=primary_summary.average_price,
        reference_trade_median_price=primary_summary.median_price,
        premium_amount=premium_amount,
        premium_rate=premium_rate,
        sample_size=primary_summary.sample_size,
        latest_trade_date=primary_summary.latest_trade_date,
        judgement=judgement,
        judgement_reason=reason,
    )


def _parse_trade_date(value: Any) -> Optional[date]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _subtract_years(reference_date: date, years: int) -> date:
    try:
        return reference_date.replace(year=reference_date.year - years)
    except ValueError:
        return reference_date.replace(month=2, day=28, year=reference_date.year - years)


def _safe_average(values: List[int]) -> Optional[int]:
    if not values:
        return None
    return round(sum(values) / len(values))


def _safe_median(values: List[int]) -> Optional[int]:
    if not values:
        return None
    return round(median(values))


def _stringify(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
