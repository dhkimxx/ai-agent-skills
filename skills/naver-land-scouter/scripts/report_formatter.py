from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from .constants import PYEONG_TO_SQUARE_METER
from .schemas import (
    ComparisonItem,
    ComparisonResult,
    ComplexReport,
    HybridReportPayload,
    ListingResult,
    NormalizedArticle,
    NormalizedComplex,
    NormalizedPriceSummary,
    NormalizedRealTradeRecord,
    NormalizedSchool,
    NormalizedTransport,
)


def format_hybrid_report(payload: HybridReportPayload) -> str:
    summary_lines = _build_summary(payload)
    table_lines = _build_table(payload)
    detail_lines = _build_details(payload)
    json_block = _build_json_block(payload)

    sections = [
        "# 네이버 부동산 스카우터 리포트",
        "## 핵심 요약",
        *summary_lines,
        "",
        "## 비교 표",
        *table_lines,
    ]

    if detail_lines:
        sections.extend(["", "## 상세", *detail_lines])

    sections.extend(["", json_block])
    return "\n".join(sections)


def _build_summary(payload: HybridReportPayload) -> List[str]:
    summary = [
        f"- 워크플로우: {payload.workflow}",
        f"- 생성 시각(UTC): {_format_timestamp(payload.generated_at)}",
    ]

    if payload.listing_result:
        summary.append(
            f"- 매물 수: {len(payload.listing_result.items)}건"
        )

    if payload.complex_report:
        complex_summary = _format_complex_title(payload.complex_report.complex)
        summary.append(f"- 단지: {complex_summary}")

    if payload.comparison_result:
        summary.append(
            f"- 비교 대상: {len(payload.comparison_result.items)}건"
        )

    if payload.investment_indicator_result:
        gap = _format_price(payload.investment_indicator_result.gap_amount)
        yield_rate = _format_percentage(payload.investment_indicator_result.yield_rate)
        summary.append(f"- Gap: {gap}")
        summary.append(f"- Yield: {yield_rate}")

    return summary


def _build_table(payload: HybridReportPayload) -> List[str]:
    if payload.comparison_result:
        return _build_comparison_table(payload.comparison_result)
    if payload.listing_result:
        return _build_listing_table(payload.listing_result)
    if payload.complex_report:
        return _build_complex_summary_table(payload.complex_report)
    if payload.investment_indicator_result:
        return _build_investment_table(payload.investment_indicator_result)
    return ["| 항목 | 값 |", "| --- | --- |", "| 데이터 | 없음 |"]


def _build_details(payload: HybridReportPayload) -> List[str]:
    details: List[str] = []

    if payload.complex_report:
        details.extend(_build_complex_details(payload.complex_report))

    if payload.listing_result:
        details.extend(_build_listing_details(payload.listing_result))

    if payload.comparison_result and payload.comparison_result.recommendation:
        details.append(f"- 추천 사유: {payload.comparison_result.recommendation}")

    if payload.investment_indicator_result:
        for note in payload.investment_indicator_result.notes:
            details.append(f"- 참고: {note}")

    return details


def _build_listing_table(result: ListingResult) -> List[str]:
    header = "| 매물명 | 거래 | 가격(만원) | 면적 | 층/향 |"
    separator = "| --- | --- | --- | --- | --- |"
    rows = [header, separator]

    for item in result.items:
        rows.append(
            "| {name} | {trade} | {price} | {area} | {floor} |".format(
                name=item.article_name or "-",
                trade=item.trade_type or "-",
                price=_format_price(item.price),
                area=_format_article_area(item),
                floor=_format_floor_direction(item),
            )
        )

    if len(rows) == 2:
        rows.append("| 데이터 | 없음 | - | - | - |")

    return rows


def _build_comparison_table(result: ComparisonResult) -> List[str]:
    header = "| 매물명 | 점수 | 가격(만원) | 면적 | 요약 |"
    separator = "| --- | --- | --- | --- | --- |"
    rows = [header, separator]

    for item in result.items:
        rows.append(
            "| {name} | {score} | {price} | {area} | {reason} |".format(
                name=item.article.article_name or "-",
                score=_format_score(item.score),
                price=_format_price(item.article.price),
                area=_format_article_area(item.article),
                reason=item.score_reason or "-",
            )
        )

    if len(rows) == 2:
        rows.append("| 데이터 | - | - | - | 없음 |")

    return rows


def _build_complex_summary_table(report: ComplexReport) -> List[str]:
    header = "| 항목 | 값 |"
    separator = "| --- | --- |"
    rows = [header, separator]

    complex_summary = _format_complex_title(report.complex)
    rows.append(f"| 단지 | {complex_summary} |")
    rows.append(
        f"| 세대수 | {_format_optional_int(report.complex.total_household_count if report.complex else None)} |"
    )
    rows.append(
        f"| 준공년도 | {_format_optional_int(report.complex.completion_year if report.complex else None)} |"
    )

    price_summary = report.price_summary
    if price_summary:
        rows.append(
            "| 시세 범위 | {min} ~ {max} |".format(
                min=_format_price(price_summary.minimum_price),
                max=_format_price(price_summary.maximum_price),
            )
        )
        rows.append(
            f"| 평균 시세 | {_format_price(price_summary.average_price)} |"
        )

    rows.append(f"| 학군 | {len(report.schools)}곳 |")
    rows.append(f"| 교통/편의 | {len(report.transports)}곳 |")
    rows.append(f"| 실거래 | {len(report.real_trade_records)}건 |")

    return rows


def _build_investment_table(result) -> List[str]:
    header = "| 지표 | 값 |"
    separator = "| --- | --- |"
    rows = [header, separator]
    rows.append(f"| Gap | {_format_price(result.gap_amount)} |")
    rows.append(f"| Yield | {_format_percentage(result.yield_rate)} |")
    return rows


def _build_complex_details(report: ComplexReport) -> List[str]:
    details: List[str] = []
    if report.schools:
        details.append("- 학군: " + ", ".join(_format_school(s) for s in report.schools))
    if report.transports:
        details.append(
            "- 교통/편의: " + ", ".join(_format_transport(t) for t in report.transports)
        )
    if report.real_trade_records:
        details.append(
            "- 실거래: "
            + "; ".join(_format_trade_record(r) for r in report.real_trade_records[:5])
        )
    return details


def _build_listing_details(result: ListingResult) -> List[str]:
    details: List[str] = []
    for item in result.items[:5]:
        if item.article_feature_description:
            details.append(
                f"- {item.article_name or item.article_no}: {item.article_feature_description}"
            )
    return details


def _build_json_block(payload: HybridReportPayload) -> str:
    json_payload = payload.model_dump(by_alias=True, exclude_none=True)
    json_payload.setdefault("generatedAt", _utc_now())
    pretty = json.dumps(json_payload, ensure_ascii=False, indent=2)

    # 상세 내용은 접어두고 필요할 때만 펼칠 수 있게 한다.
    return (
        "<details>\n"
        "<summary>시스템 연동용 JSON</summary>\n\n"
        "```json\n"
        f"{pretty}\n"
        "```\n"
        "</details>"
    )


def _format_complex_title(complex_info: Optional[NormalizedComplex]) -> str:
    if not complex_info:
        return "-"
    name = complex_info.complex_name or "-"
    address = complex_info.address or "-"
    return f"{name} ({address})"


def _format_floor_direction(article: NormalizedArticle) -> str:
    floor = article.floor_info or "-"
    direction = article.direction or "-"
    return f"{floor} / {direction}"


def _format_price(value: Optional[int], raw: bool = False) -> str:
    if value is None:
        return "-"
    if raw:
        return f"{value:,}"

    sign = "-" if value < 0 else ""
    absolute = abs(value)
    if absolute >= 10000:
        major = absolute // 10000
        minor = absolute % 10000
        if minor == 0:
            return f"{sign}{major}억"
        return f"{sign}{major}억 {minor:,}만"
    return f"{sign}{absolute:,}만"


def _format_area(value: Optional[float]) -> str:
    if value is None:
        return "-"
    pyeong = value / PYEONG_TO_SQUARE_METER
    return f"{value:.1f}㎡ ({pyeong:.1f}평)"


def _format_article_area(article: NormalizedArticle) -> str:
    supply_area = article.supply_area or article.area
    exclusive_area = article.exclusive_area

    if supply_area is not None and exclusive_area is not None:
        if round(supply_area, 2) != round(exclusive_area, 2):
            return f"공급 {_format_area(supply_area)} / 전용 {_format_area(exclusive_area)}"

    return _format_area(exclusive_area or supply_area)


def _format_percentage(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}%"


def _format_score(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _format_optional_int(value: Optional[int]) -> str:
    if value is None:
        return "-"
    return f"{value}"


def _format_school(school: NormalizedSchool) -> str:
    name = school.school_name or "-"
    school_type = school.school_type or "-"
    distance = f"{school.distance}m" if school.distance is not None else "거리 정보 없음"
    return f"{name}({school_type}, {distance})"


def _format_transport(transport: NormalizedTransport) -> str:
    name = transport.place_name or "-"
    category = transport.category or "-"
    distance = (
        f"{transport.distance}m" if transport.distance is not None else "거리 정보 없음"
    )
    return f"{name}({category}, {distance})"


def _format_trade_record(record: NormalizedRealTradeRecord) -> str:
    date = record.trade_date or "-"
    price = _format_price(record.price)
    floor = record.floor or "-"
    return f"{date} {price} {floor}층"


def _format_timestamp(value: Optional[str]) -> str:
    if value:
        return value
    return _utc_now()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
