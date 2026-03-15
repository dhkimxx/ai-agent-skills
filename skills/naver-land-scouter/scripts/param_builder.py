from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from .area_range import parse_area_range, parse_area_range_expression
from .normalization import normalize_area_to_square_meter, normalize_price_to_manwon
from .schemas import BoundingBox, ComplexAnalysisInput, ListingSearchInput, PriceRange


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
        "priceType": price_type,
        "isPresale": is_presale,
    }
    params.update(build_bounding_box_params(bounding_box))
    return _filter_empty_params(params)


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
    parsed_min = parse_area_range_expression(minimum)
    if parsed_min:
        return _filter_empty_params({"areaMin": parsed_min[0], "areaMax": parsed_min[1]})

    parsed_max = parse_area_range_expression(maximum)
    if parsed_max:
        return _filter_empty_params({"areaMin": parsed_max[0], "areaMax": parsed_max[1]})

    if isinstance(minimum, str):
        parsed_single = parse_area_range(minimum)
        if parsed_single:
            return _filter_empty_params({"areaMin": parsed_single[0], "areaMax": parsed_single[1]})

    if isinstance(maximum, str):
        parsed_single = parse_area_range(maximum)
        if parsed_single:
            return _filter_empty_params({"areaMin": parsed_single[0], "areaMax": parsed_single[1]})

    return _filter_empty_params(
        {
            "areaMin": normalize_area_to_square_meter(minimum),
            "areaMax": normalize_area_to_square_meter(maximum),
        }
    )


def _join_filter_values(values: Optional[Iterable[str]]) -> Optional[str]:
    if not values:
        return None
    filtered = [value for value in values if value]
    if not filtered:
        return None
    # 네이버 필터는 콜론 구분 문자열을 쓰는 경우가 많아 통일한다.
    return ":".join(filtered)


def _filter_empty_params(params: Dict[str, Any]) -> Dict[str, Any]:
    filtered: Dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, str) and not value:
            continue
        if isinstance(value, (list, tuple, set)) and not value:
            continue
        # 불필요한 기본값 전송은 검색 결과에 영향을 주기 때문에 제거한다.
        filtered[key] = value
    return filtered
