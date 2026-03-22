from __future__ import annotations

from typing import Optional

from ..normalization import normalize_price_to_manwon
from ..schemas import InvestmentIndicatorInput, InvestmentIndicatorResult, RawArticleDetail
from .article_payload import flatten_article_payload
from .contracts import NaverLandRepository
from .errors import ServiceError, build_service_error


class InvestmentIndicatorService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def calculate_indicator(
        self, investment_input: InvestmentIndicatorInput
    ) -> InvestmentIndicatorResult:
        if not investment_input.article_no:
            return InvestmentIndicatorResult(
                notes=[
                    "투자 지표 계산에는 매물 ID(article_no)가 필요합니다.",
                    "단지 기준 계산은 매매/전세 tradeType 확보 후 확장합니다.",
                ]
            )

        try:
            payload, context = self._repository.fetch_article_detail(
                investment_input.article_no
            )
            parsed = RawArticleDetail.model_validate(flatten_article_payload(payload))
            sale_price = normalize_price_to_manwon(parsed.deal_price or parsed.price)
            rent_price = normalize_price_to_manwon(parsed.rent_price)

            gap_amount: Optional[int] = None
            yield_rate: Optional[float] = None
            notes = []

            if sale_price is None:
                notes.append("매매가 정보를 확인할 수 없습니다.")
            if rent_price is None:
                notes.append("전세/월세 정보를 확인할 수 없습니다.")

            if sale_price is not None and rent_price is not None:
                gap_amount = sale_price - rent_price
                if sale_price > 0:
                    # 수익률은 퍼센트 표현이므로 소수점 둘째 자리까지 제한한다.
                    yield_rate = round((rent_price / sale_price) * 100, 2)

            return InvestmentIndicatorResult(
                gap_amount=gap_amount,
                yield_rate=yield_rate,
                notes=notes,
                sources=[context],
            )
        except Exception as exc:  # noqa: BLE001 - 서비스 공통 에러로 변환한다.
            raise build_service_error(
                exc,
                error_code="INVESTMENT_INDICATOR_FAILED",
                message="투자 지표 계산에 실패했습니다.",
                details={"article_no": investment_input.article_no},
            ) from exc
