from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from .area_range import parse_area_range, parse_area_range_expression
from .normalization import normalize_area_to_square_meter, normalize_price_to_manwon
from .schemas import BoundingBox, ComplexAnalysisInput, ListingSearchInput, PriceRange

MARKER_RANGE_MAX = 900000000


def build_listing_search_params(listing_input: ListingSearchInput) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "realEstateType": listing_input.real_estate_type,
        "tradeType": listing_input.trade_type,
        "order": listing_input.order,
        "page": listing_input.page,
        "directions": _join_filter_values(listing_input.directions),
    }

    if listing_input.price_range:
        params.update(_build_price_range_params(listing_input.price_range, "price"))

    if listing_input.rent_price_range:
        params.update(
            _build_price_range_params(listing_input.rent_price_range, "rentPrice")
        )

    if listing_input.area_range:
        params.update(
            _build_area_range_params(
                listing_input.area_range.minimum, listing_input.area_range.maximum
            )
        )

    return _filter_empty_params(params)


def build_article_list_params(
    complex_no: str,
    listing_input: ListingSearchInput,
    price_type: Optional[str] = None,
    show_article: Optional[bool] = None,
    same_address_group: Optional[bool] = None,
) -> Dict[str, Any]:
    params = build_listing_search_params(listing_input)
    params.update(
        {
            "complexNo": complex_no,
            "type": "list",
            "priceType": price_type,
            "showArticle": show_article,
            "sameAddressGroup": same_address_group,
        }
    )
    return _filter_empty_params(params)


def build_cortars_params(center_lat: float, center_lon: float, zoom: int) -> Dict[str, Any]:
    return _filter_empty_params(
        {"centerLat": center_lat, "centerLon": center_lon, "zoom": zoom}
    )


def build_marker_params(
    cortar_no: str,
    bounding_box: BoundingBox,
    zoom: int,
    real_estate_type: str,
    price_type: Optional[str] = None,
    is_presale: Optional[bool] = None,
) -> Dict[str, Any]:
    params = {
        "cortarNo": cortar_no,
        "zoom": zoom,
        "realEstateType": real_estate_type,
        "priceType": price_type or "RETAIL",
        "isPresale": True if is_presale is None else is_presale,
        "markerId": "",
        "markerType": "",
        "selectedComplexNo": "",
        "selectedComplexBuildingNo": "",
        "fakeComplexMarker": "",
        "tradeType": "",
        "tag": "::::::::",
        "rentPriceMin": 0,
        "rentPriceMax": MARKER_RANGE_MAX,
        "priceMin": 0,
        "priceMax": MARKER_RANGE_MAX,
        "areaMin": 0,
        "areaMax": MARKER_RANGE_MAX,
        "oldBuildYears": "",
        "recentlyBuildYears": "",
        "minHouseHoldCount": "",
        "maxHouseHoldCount": "",
        "showArticle": False,
        "sameAddressGroup": False,
        "minMaintenanceCost": "",
        "maxMaintenanceCost": "",
        "directions": "",
    }
    params.update(build_bounding_box_params(bounding_box))
    return _filter_empty_params(
        params,
        preserve_empty_string_keys={
            "markerId",
            "markerType",
            "selectedComplexNo",
            "selectedComplexBuildingNo",
            "fakeComplexMarker",
            "tradeType",
            "oldBuildYears",
            "recentlyBuildYears",
            "minHouseHoldCount",
            "maxHouseHoldCount",
            "minMaintenanceCost",
            "maxMaintenanceCost",
            "directions",
        },
    )


def build_complex_price_params(
    complex_input: ComplexAnalysisInput,
    result_type: str,
    year: Optional[int] = None,
    area_no: Optional[str] = None,
    trade_type: Optional[str] = None,
) -> Dict[str, Any]:
    params = {
        "complexNo": complex_input.complex_no,
        "tradeType": trade_type or complex_input.trade_type,
        "year": year or complex_input.year,
        "type": result_type,
        "areaNo": area_no or complex_input.area_no,
    }
    return _filter_empty_params(params)


def build_real_trade_params(
    complex_input: ComplexAnalysisInput,
    area_no: Optional[str] = None,
    trade_type: Optional[str] = None,
) -> Dict[str, Any]:
    params = {
        "complexNo": complex_input.complex_no,
        "tradeType": trade_type or complex_input.trade_type,
        "type": "table",
        "areaNo": area_no or complex_input.area_no,
    }
    return _filter_empty_params(params)


def build_neighborhood_params(
    bounding_box: BoundingBox, zoom: int, category_type: str = "BUS"
) -> Dict[str, Any]:
    params = {"type": category_type, "zoom": zoom}
    params.update(build_bounding_box_params(bounding_box))
    return _filter_empty_params(params)


def build_bounding_box_params(bounding_box: BoundingBox) -> Dict[str, Any]:
    return _filter_empty_params(
        {
            "leftLon": bounding_box.left_lon,
            "rightLon": bounding_box.right_lon,
            "topLat": bounding_box.top_lat,
            "bottomLat": bounding_box.bottom_lat,
        }
    )


def _build_price_range_params(price_range: PriceRange, prefix: str) -> Dict[str, Any]:
    return _filter_empty_params(
        {
            f"{prefix}Min": normalize_price_to_manwon(price_range.minimum),
            f"{prefix}Max": normalize_price_to_manwon(price_range.maximum),
        }
    )


def _build_area_range_params(
    minimum: Optional[float | str], maximum: Optional[float | str]
) -> Dict[str, Any]:
    area_min, area_max = resolve_area_range_bounds(minimum, maximum)
    return _filter_empty_params({"areaMin": area_min, "areaMax": area_max})


def resolve_area_range_bounds(
    minimum: Optional[float | str], maximum: Optional[float | str]
) -> tuple[Optional[float], Optional[float]]:
    parsed_min = parse_area_range_expression(minimum)
    if parsed_min:
        return parsed_min[0], parsed_min[1]

    parsed_max = parse_area_range_expression(maximum)
    if parsed_max:
        return parsed_max[0], parsed_max[1]

    parsed_single_min = _parse_single_area_bound(minimum)
    parsed_single_max = _parse_single_area_bound(maximum)

    area_min = parsed_single_min[0] if parsed_single_min else None
    area_max = parsed_single_max[1] if parsed_single_max else None
    return area_min, area_max


def _parse_single_area_bound(
    value: Optional[float | str],
) -> Optional[tuple[float, float]]:
    if value is None:
        return None
    if isinstance(value, str):
        return parse_area_range(value)

    normalized = normalize_area_to_square_meter(value)
    if normalized is None:
        return None
    return normalized, normalized


def _join_filter_values(values: Optional[Iterable[str]]) -> Optional[str]:
    if not values:
        return None
    filtered = [value for value in values if value]
    if not filtered:
        return None
    # 네이버 필터는 콜론 구분 문자열을 쓰는 경우가 많아 통일한다.
    return ":".join(filtered)


def _filter_empty_params(
    params: Dict[str, Any],
    preserve_empty_string_keys: Optional[set[str]] = None,
) -> Dict[str, Any]:
    preserved_keys = preserve_empty_string_keys or set()
    filtered: Dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, str) and not value and key not in preserved_keys:
            continue
        if isinstance(value, (list, tuple, set)) and not value:
            continue
        # 불필요한 기본값 전송은 검색 결과에 영향을 주기 때문에 제거한다.
        filtered[key] = value
    return filtered
