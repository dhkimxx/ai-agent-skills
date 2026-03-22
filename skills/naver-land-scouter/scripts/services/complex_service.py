from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..normalization import normalize_price_to_manwon
from ..param_builder import (
    build_complex_price_params,
    build_neighborhood_params,
    build_real_trade_params,
)
from ..schemas import (
    ApiRequestContext,
    BoundingBox,
    ComplexAnalysisInput,
    ComplexReport,
    NormalizedComplex,
    NormalizedPriceSummary,
    NormalizedRealTradeRecord,
    NormalizedSchool,
    NormalizedTransport,
    RawComplexDetail,
    RawComplexOverview,
    RawNeighborhoodInfo,
    RawPriceSummary,
    RawRealTradeRecord,
    RawSchoolInfo,
)
from .contracts import NaverLandRepository
from .errors import ServiceError, build_service_error


class ComplexAnalysisService:
    def __init__(self, repository: NaverLandRepository) -> None:
        self._repository = repository

    def create_report(
        self,
        complex_input: ComplexAnalysisInput,
        transport_bounding_box: Optional[BoundingBox] = None,
        transport_zoom: Optional[int] = None,
        include_schools: bool = True,
        include_real_trades: bool = True,
    ) -> ComplexReport:
        sources: List[ApiRequestContext] = []
        try:
            overview_payload, overview_context = self._repository.fetch_complex_overview(
                complex_input.complex_no
            )
            sources.append(overview_context)
            detail_payload, detail_context = self._repository.fetch_complex_detail(
                complex_input.complex_no
            )
            sources.append(detail_context)

            complex_summary = _merge_complex_models(
                overview_payload, detail_payload
            )

            price_payload, price_context = self._repository.fetch_complex_prices(
                complex_input.complex_no,
                build_complex_price_params(complex_input, result_type="summary"),
            )
            sources.append(price_context)
            price_summary = _extract_price_summary(price_payload)

            real_trade_records: List[NormalizedRealTradeRecord] = []
            if include_real_trades:
                trade_payload, trade_context = self._repository.fetch_real_trade_records(
                    complex_input.complex_no,
                    build_real_trade_params(complex_input),
                )
                sources.append(trade_context)
                real_trade_records = _extract_real_trade_records(trade_payload)

            schools: List[NormalizedSchool] = []
            if include_schools:
                school_payload, school_context = self._repository.fetch_schools(
                    complex_input.complex_no
                )
                sources.append(school_context)
                schools = _extract_school_infos(school_payload)

            transports: List[NormalizedTransport] = []
            if transport_bounding_box and transport_zoom is not None:
                transport_payload, transport_context = (
                    self._repository.fetch_neighborhoods(
                        build_neighborhood_params(
                            transport_bounding_box, transport_zoom
                        )
                    )
                )
                sources.append(transport_context)
                transports = _extract_transport_infos(transport_payload)

            return ComplexReport(
                complex=complex_summary,
                price_summary=price_summary,
                real_trade_records=real_trade_records,
                schools=schools,
                transports=transports,
                sources=sources,
            )
        except Exception as exc:  # noqa: BLE001 - 서비스 공통 에러로 변환한다.
            raise build_service_error(
                exc,
                error_code="COMPLEX_REPORT_FAILED",
                message="단지 리포트 생성에 실패했습니다.",
                details={"complex_no": complex_input.complex_no},
            ) from exc


def _merge_complex_models(
    overview_payload: Any, detail_payload: Any
) -> Optional[NormalizedComplex]:
    overview = (
        RawComplexOverview.model_validate(overview_payload)
        if isinstance(overview_payload, dict)
        else RawComplexOverview()
    )
    detail = (
        RawComplexDetail.model_validate(detail_payload)
        if isinstance(detail_payload, dict)
        else RawComplexDetail()
    )

    if not (overview.complex_no or detail.complex_no):
        return None

    return NormalizedComplex(
        complex_no=detail.complex_no or overview.complex_no,
        complex_name=detail.complex_name or overview.complex_name,
        address=detail.address or overview.address,
        total_household_count=detail.total_household_count
        or overview.total_household_count,
        completion_year=overview.completion_year,
    )


def _extract_price_summary(payload: Any) -> Optional[NormalizedPriceSummary]:
    if payload is None:
        return None

    raw_summary: Dict[str, Any] | None = None
    if isinstance(payload, dict):
        if isinstance(payload.get("summary"), dict):
            raw_summary = payload.get("summary")
        elif isinstance(payload.get("priceSummary"), dict):
            raw_summary = payload.get("priceSummary")
        else:
            raw_summary = payload
    elif isinstance(payload, list) and payload:
        first_item = payload[0]
        if isinstance(first_item, dict):
            raw_summary = first_item

    if not raw_summary:
        return None

    parsed = RawPriceSummary.model_validate(raw_summary)
    return NormalizedPriceSummary(
        minimum_price=normalize_price_to_manwon(parsed.minimum_price),
        maximum_price=normalize_price_to_manwon(parsed.maximum_price),
        average_price=normalize_price_to_manwon(parsed.average_price),
    )


def _extract_real_trade_records(payload: Any) -> List[NormalizedRealTradeRecord]:
    raw_items = _extract_list_payload(payload)
    records: List[NormalizedRealTradeRecord] = []
    for item in raw_items:
        parsed = RawRealTradeRecord.model_validate(item)
        records.append(
            NormalizedRealTradeRecord(
                trade_date=parsed.trade_date,
                price=normalize_price_to_manwon(parsed.price),
                area_no=parsed.area_no,
                floor=parsed.floor,
            )
        )
    return records


def _extract_school_infos(payload: Any) -> List[NormalizedSchool]:
    raw_items = _extract_list_payload(payload)
    schools: List[NormalizedSchool] = []
    for item in raw_items:
        parsed = RawSchoolInfo.model_validate(item)
        schools.append(
            NormalizedSchool(
                school_name=parsed.school_name,
                school_type=parsed.school_type,
                distance=parsed.distance,
                address=parsed.address,
            )
        )
    return schools


def _extract_transport_infos(payload: Any) -> List[NormalizedTransport]:
    raw_items = _extract_list_payload(payload)
    transports: List[NormalizedTransport] = []
    for item in raw_items:
        parsed = RawNeighborhoodInfo.model_validate(item)
        transports.append(
            NormalizedTransport(
                place_name=parsed.place_name,
                category=parsed.category,
                distance=parsed.distance,
            )
        )
    return transports


def _extract_list_payload(payload: Any) -> List[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("list"), list):
            return [item for item in payload.get("list") if isinstance(item, dict)]
        if isinstance(payload.get("result"), list):
            return [item for item in payload.get("result") if isinstance(item, dict)]
        if isinstance(payload.get("schools"), list):
            return [item for item in payload.get("schools") if isinstance(item, dict)]
        if isinstance(payload.get("neighborhoods"), list):
            return [item for item in payload.get("neighborhoods") if isinstance(item, dict)]
        if isinstance(payload.get("data"), list):
            return [item for item in payload.get("data") if isinstance(item, dict)]
    return []
