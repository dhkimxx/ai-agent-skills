from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

from .naver_land_client import NaverLandApiClient
from .naver_land_repository import DefaultNaverLandRepository
from .report_formatter import format_hybrid_report, format_json_report
from .schemas import (
    BoundingBox,
    ComplexAnalysisInput,
    HistoryInput,
    HybridReportPayload,
    InvestmentIndicatorInput,
    ListingSearchInput,
)
from .services import (
    ComparisonService,
    ComplexAnalysisService,
    DiscoveryService,
    HistoryService,
    InvestmentIndicatorService,
    ListingService,
    LocationService,
    ScanService,
    ServiceError,
)
from .location_utils import build_bounding_box_from_radius, parse_radius_to_meters


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="네이버 부동산 스카우터 CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("listings", help="단지 매물 리스트 조회")
    list_parser.add_argument("--complex-no", required=True)
    _add_listing_filter_arguments(list_parser)

    complex_parser = subparsers.add_parser("complex", help="단지 리포트")
    complex_parser.add_argument("--complex-no", required=True)
    complex_parser.add_argument("--trade-type")
    complex_parser.add_argument("--area-no")
    complex_parser.add_argument("--year", type=int)
    complex_parser.add_argument("--transport-zoom", type=int)
    complex_parser.add_argument("--bbox", nargs=4, type=float, metavar=("LEFT", "RIGHT", "TOP", "BOTTOM"))
    complex_parser.add_argument("--no-schools", action="store_true")
    complex_parser.add_argument("--no-real-trades", action="store_true")

    compare_parser = subparsers.add_parser("compare", help="매물 비교")
    compare_parser.add_argument("--article-no", action="append", required=True)

    invest_parser = subparsers.add_parser("invest", help="투자 지표")
    invest_parser.add_argument("--article-no", required=True)

    history_parser = subparsers.add_parser("history", help="실거래 히스토리")
    history_target_group = history_parser.add_mutually_exclusive_group(required=True)
    history_target_group.add_argument("--article-no")
    history_target_group.add_argument("--complex-no")
    history_parser.add_argument("--trade-type")
    history_parser.add_argument("--area-no")

    search_parser = subparsers.add_parser("search", help="위치/단지 검색")
    search_parser.add_argument("query_text")
    search_parser.add_argument("--radius", default="700m")
    search_parser.add_argument("--real-estate-type", default="APT")
    search_parser.add_argument(
        "--enrich",
        choices=["complex-summary"],
        default=None,
    )

    discover_parser = subparsers.add_parser("discover", help="지도 기반 탐색")
    discover_parser.add_argument("--near")
    discover_parser.add_argument("--radius", default="500m")
    discover_parser.add_argument("--center-lat", type=float)
    discover_parser.add_argument("--center-lon", type=float)
    discover_parser.add_argument("--zoom", type=int)
    discover_parser.add_argument("--left-lon", type=float)
    discover_parser.add_argument("--right-lon", type=float)
    discover_parser.add_argument("--top-lat", type=float)
    discover_parser.add_argument("--bottom-lat", type=float)
    discover_parser.add_argument("--real-estate-type", required=True)
    discover_parser.add_argument("--price-type")
    discover_parser.add_argument("--is-presale", action="store_true")
    discover_parser.add_argument(
        "--enrich",
        choices=["complex-summary"],
        default=None,
    )

    scan_parser = subparsers.add_parser("scan", help="여러 위치 통합 검색")
    scan_parser.add_argument("--near", action="append", required=True)
    scan_parser.add_argument("--radius", default="500m")
    scan_parser.add_argument("--real-estate-type", required=True)
    scan_parser.add_argument("--complex-limit", type=int, default=12)
    scan_parser.add_argument(
        "--enrich",
        choices=["complex-summary"],
        default=None,
    )
    _add_listing_filter_arguments(scan_parser, include_real_estate_type=False)

    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="추가 헤더 (예: 'Referer:https://new.land.naver.com/')",
    )
    parser.add_argument(
        "--cookie",
        action="append",
        default=[],
        help="추가 쿠키 (예: 'NID_SES=...')",
    )
    parser.add_argument(
        "--bootstrap-mode",
        choices=["auto", "none", "http", "browser"],
        default=None,
        help="세션 부트스트랩 방식 (기본값: auto)",
    )
    parser.add_argument(
        "--format",
        choices=["hybrid", "json"],
        default="hybrid",
        help="출력 형식",
    )
    parser.add_argument(
        "--output-file",
        help="결과를 저장할 파일 경로",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    env_headers = _read_env_headers()
    env_cookies = _read_env_cookies()
    headers = {**env_headers, **_parse_headers(args.header)}
    cookies = {**env_cookies, **_parse_cookies(args.cookie)}
    bootstrap_mode = args.bootstrap_mode or os.getenv(
        "NAVER_LAND_BOOTSTRAP_MODE", "auto"
    )

    client = NaverLandApiClient(
        headers=headers or None,
        cookies=cookies or None,
        bootstrap_mode=bootstrap_mode,
    )
    repository = DefaultNaverLandRepository(client)

    try:
        if args.command == "listings":
            listing_input = _build_listing_input(args)
            service = ListingService(repository)
            result = service.search_by_complex(args.complex_no, listing_input)
            payload = HybridReportPayload(
                workflow="listings",
                listing_result=result,
            )
        elif args.command == "complex":
            service = ComplexAnalysisService(repository)
            complex_input = ComplexAnalysisInput(
                complex_no=args.complex_no,
                trade_type=args.trade_type,
                area_no=args.area_no,
                year=args.year,
            )
            transport_bbox = _build_bbox(args)
            report = service.create_report(
                complex_input,
                transport_bounding_box=transport_bbox,
                transport_zoom=args.transport_zoom,
                include_schools=not args.no_schools,
                include_real_trades=not args.no_real_trades,
            )
            payload = HybridReportPayload(
                workflow="complex",
                complex_report=report,
            )
        elif args.command == "compare":
            service = ComparisonService(repository)
            comparison_result = service.compare_articles(args.article_no)
            payload = HybridReportPayload(
                workflow="compare",
                comparison_result=comparison_result,
            )
        elif args.command == "invest":
            service = InvestmentIndicatorService(repository)
            investment_result = service.calculate_indicator(
                InvestmentIndicatorInput(article_no=args.article_no)
            )
            payload = HybridReportPayload(
                workflow="invest",
                investment_indicator_result=investment_result,
            )
        elif args.command == "history":
            service = HistoryService(repository)
            history_result = service.create_history(_build_history_input(args))
            payload = HybridReportPayload(
                workflow="history",
                history_result=history_result,
            )
        elif args.command == "search":
            service = LocationService(repository)
            search_result = service.search(
                query_text=args.query_text,
                radius_meters=parse_radius_to_meters(args.radius),
                real_estate_type=args.real_estate_type,
                enrich_mode=args.enrich,
            )
            payload = HybridReportPayload(
                workflow="search",
                search_result=search_result,
            )
        elif args.command == "discover":
            location_service = LocationService(repository)
            service = DiscoveryService(repository)
            center_lat, center_lon, zoom, bounding_box = _resolve_discover_request(
                args,
                location_service,
            )
            listing_result = service.discover_by_map(
                center_lat=center_lat,
                center_lon=center_lon,
                zoom=zoom,
                bounding_box=bounding_box,
                real_estate_type=args.real_estate_type,
                price_type=args.price_type,
                is_presale=args.is_presale,
                enrich_mode=args.enrich,
            )
            payload = HybridReportPayload(
                workflow="discover",
                listing_result=listing_result,
            )
        elif args.command == "scan":
            service = ScanService(repository)
            listing_input = _build_listing_input(args)
            scan_result = service.scan_near_queries(
                near_queries=args.near,
                radius_meters=parse_radius_to_meters(args.radius),
                real_estate_type=args.real_estate_type,
                listing_input=listing_input,
                enrich_mode=args.enrich,
                complex_limit=args.complex_limit,
                expand_articles=_should_expand_scan_articles(args),
            )
            payload = HybridReportPayload(
                workflow="scan",
                scan_result=scan_result,
            )
        else:
            raise ServiceError(
                error_code="UNKNOWN_COMMAND",
                message="지원하지 않는 커맨드입니다.",
            )

        payload.generated_at = _utc_now()
        report = _render_report(payload, args.format)
        _write_output_if_requested(args.output_file, report)
        if args.output_file:
            print(_build_output_notice(payload, args.output_file, args.format))
        else:
            print(report)
    except ServiceError as exc:
        print(_format_service_error(exc))
    finally:
        client.close()


def _parse_headers(raw_headers: list[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for item in raw_headers:
        if not item:
            continue
        if ":" not in item:
            raise ServiceError(
                error_code="HEADER_FORMAT_INVALID",
                message="헤더 형식이 잘못되었습니다. 'Key:Value'로 입력하세요.",
                details={"value": item},
            )
        key, value = item.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def _parse_cookies(raw_cookies: list[str]) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    for item in raw_cookies:
        if not item:
            continue
        if "=" not in item:
            raise ServiceError(
                error_code="COOKIE_FORMAT_INVALID",
                message="쿠키 형식이 잘못되었습니다. 'Key=Value'로 입력하세요.",
                details={"value": item},
            )
        key, value = item.split("=", 1)
        cookies[key.strip()] = value.strip()
    return cookies


def _read_env_headers() -> Dict[str, str]:
    raw = os.getenv("NAVER_LAND_HEADERS")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(key): str(value) for key, value in parsed.items()}
    except json.JSONDecodeError:
        pass
    return _parse_headers(_split_env_items(raw))


def _read_env_cookies() -> Dict[str, str]:
    raw = os.getenv("NAVER_LAND_COOKIES") or os.getenv("NAVER_LAND_COOKIE")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(key): str(value) for key, value in parsed.items()}
    except json.JSONDecodeError:
        pass
    return _parse_cookies(_split_env_items(raw))


def _split_env_items(raw: str) -> list[str]:
    items = re.split(r"[;\n]+", raw)
    return [item.strip() for item in items if item.strip()]


def _build_listing_input(args: argparse.Namespace) -> ListingSearchInput:
    price_range = _build_price_range(args.price_min, args.price_max)
    area_range = _build_area_range(args.area_min, args.area_max)
    exclusive_area_range = _build_area_range(
        args.exclusive_area_min,
        args.exclusive_area_max,
    )
    _validate_center_coordinates(args.center_lat, args.center_lon)

    return ListingSearchInput(
        query_text="manual",
        real_estate_type=args.real_estate_type,
        trade_type=args.trade_type,
        price_range=price_range,
        area_range=area_range,
        exclusive_area_range=exclusive_area_range,
        directions=args.directions,
        order=args.order,
        page=args.page,
        center_lat=args.center_lat,
        center_lon=args.center_lon,
    )


def _add_listing_filter_arguments(
    parser: argparse.ArgumentParser,
    include_real_estate_type: bool = True,
) -> None:
    if include_real_estate_type:
        parser.add_argument("--real-estate-type")
    parser.add_argument("--trade-type")
    parser.add_argument("--price-min")
    parser.add_argument("--price-max")
    parser.add_argument("--area-min")
    parser.add_argument("--area-max")
    parser.add_argument("--exclusive-area-min")
    parser.add_argument("--exclusive-area-max")
    parser.add_argument("--order", default="rank")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--directions", nargs="*")
    parser.add_argument("--center-lat", type=float)
    parser.add_argument("--center-lon", type=float)


def _build_price_range(price_min: Optional[str], price_max: Optional[str]) -> Optional[Dict[str, Any]]:
    if price_min is None and price_max is None:
        return None
    return {"minimum": price_min, "maximum": price_max}


def _build_area_range(area_min: Optional[str], area_max: Optional[str]) -> Optional[Dict[str, Any]]:
    if area_min is None and area_max is None:
        return None
    return {"minimum": area_min, "maximum": area_max}


def _build_bbox(args: argparse.Namespace) -> Optional[BoundingBox]:
    bbox = getattr(args, "bbox", None)
    if bbox:
        left, right, top, bottom = bbox
        return BoundingBox(
            left_lon=left,
            right_lon=right,
            top_lat=top,
            bottom_lat=bottom,
        )
    if all(
        value is not None
        for value in [
            getattr(args, "left_lon", None),
            getattr(args, "right_lon", None),
            getattr(args, "top_lat", None),
            getattr(args, "bottom_lat", None),
        ]
    ):
        return BoundingBox(
            left_lon=args.left_lon,
            right_lon=args.right_lon,
            top_lat=args.top_lat,
            bottom_lat=args.bottom_lat,
        )
    return None


def _resolve_discover_request(
    args: argparse.Namespace,
    location_service: LocationService,
) -> tuple[float, float, int, BoundingBox]:
    if getattr(args, "near", None):
        resolved = location_service.resolve_single_location(args.near)
        radius_meters = parse_radius_to_meters(args.radius)
        return (
            resolved.latitude,
            resolved.longitude,
            resolved.zoom or args.zoom or 16,
            build_bounding_box_from_radius(
                resolved.latitude,
                resolved.longitude,
                radius_meters,
            ),
        )

    bounding_box = _build_bbox(args)
    if bounding_box is None:
        raise ServiceError(
            error_code="BBOX_REQUIRED",
            message="지도 탐색에는 bbox 파라미터가 필요합니다.",
        )
    if args.center_lat is None or args.center_lon is None or args.zoom is None:
        raise ServiceError(
            error_code="CENTER_REQUIRED",
            message="수동 지도 탐색에는 center-lat, center-lon, zoom이 필요합니다.",
        )
    return args.center_lat, args.center_lon, args.zoom, bounding_box


def _build_history_input(args: argparse.Namespace) -> HistoryInput:
    return HistoryInput(
        article_no=getattr(args, "article_no", None),
        complex_no=getattr(args, "complex_no", None),
        trade_type=getattr(args, "trade_type", None),
        area_no=getattr(args, "area_no", None),
    )


def _should_expand_scan_articles(args: argparse.Namespace) -> bool:
    return any(
        [
            getattr(args, "trade_type", None),
            getattr(args, "price_min", None),
            getattr(args, "price_max", None),
            getattr(args, "area_min", None),
            getattr(args, "area_max", None),
            getattr(args, "exclusive_area_min", None),
            getattr(args, "exclusive_area_max", None),
            bool(getattr(args, "directions", None)),
        ]
    )


def _render_report(payload: HybridReportPayload, output_format: str) -> str:
    if output_format == "json":
        return format_json_report(payload)
    return format_hybrid_report(payload)


def _write_output_if_requested(output_file: Optional[str], report: str) -> None:
    if not output_file:
        return

    try:
        output_path = Path(output_file).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(_ensure_trailing_newline(report), encoding="utf-8")
    except OSError as exc:
        raise ServiceError(
            error_code="OUTPUT_WRITE_FAILED",
            message="결과 파일 저장에 실패했습니다.",
            details={"path": output_file, "reason": str(exc)},
        ) from exc


def _build_output_notice(
    payload: HybridReportPayload,
    output_file: str,
    output_format: str,
) -> str:
    summary: Dict[str, Any] = {
        "outputFile": str(Path(output_file).expanduser()),
        "workflow": payload.workflow,
        "format": output_format,
    }
    if payload.listing_result:
        summary["itemCount"] = len(payload.listing_result.items)
    if payload.search_result:
        summary["candidateCount"] = len(payload.search_result.candidates)
        summary["nearbyComplexCount"] = len(payload.search_result.nearby_complexes)
    if payload.scan_result:
        summary["targetCount"] = len(payload.scan_result.targets)
        summary["itemCount"] = len(payload.scan_result.items)
    if payload.history_result:
        summary["tradePointCount"] = len(payload.history_result.trade_points)
    return json.dumps(summary, ensure_ascii=False, indent=2)


def _format_service_error(exc: ServiceError) -> str:
    payload = {
        "errorCode": exc.error_code,
        "message": exc.message,
        "details": exc.details,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_trailing_newline(value: str) -> str:
    if value.endswith("\n"):
        return value
    return f"{value}\n"


def _validate_center_coordinates(
    center_lat: Optional[float],
    center_lon: Optional[float],
) -> None:
    if center_lat is None and center_lon is None:
        return
    if center_lat is None or center_lon is None:
        raise ServiceError(
            error_code="CENTER_COORDINATE_INVALID",
            message="거리 계산을 위해서는 center-lat와 center-lon을 함께 입력해야 합니다.",
        )


if __name__ == "__main__":
    main()
