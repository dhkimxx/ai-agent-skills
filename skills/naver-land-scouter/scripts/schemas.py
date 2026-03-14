from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


def to_camel_case(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


class NaverLandBaseModel(BaseModel):
    # API 필드가 자주 변하므로 알 수 없는 필드는 무시해 안정성을 확보한다.
    # camelCase 응답을 자동 매핑해 변환 로직을 최소화한다.
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        populate_by_name=True,
        extra="ignore",
        str_strip_whitespace=True,
    )


class ApiRequestContext(NaverLandBaseModel):
    endpoint: str
    params: Optional[Dict[str, Any]] = None
    http_status: Optional[int] = None
    fetched_at: Optional[str] = None


class BoundingBox(NaverLandBaseModel):
    left_lon: Optional[float] = None
    right_lon: Optional[float] = None
    top_lat: Optional[float] = None
    bottom_lat: Optional[float] = None


class PriceRange(NaverLandBaseModel):
    # 사용자 입력은 문자열이 섞일 수 있어 유연하게 수용한다.
    minimum: Optional[float | str] = None
    maximum: Optional[float | str] = None


class AreaRange(NaverLandBaseModel):
    # 평/㎡ 입력을 모두 수용할 수 있도록 문자열도 허용한다.
    minimum: Optional[float | str] = None
    maximum: Optional[float | str] = None


class ListingSearchInput(NaverLandBaseModel):
    query_text: Optional[str] = None
    cortar_no: Optional[str] = None
    real_estate_type: Optional[str] = None
    trade_type: Optional[str] = None
    price_range: Optional[PriceRange] = None
    rent_price_range: Optional[PriceRange] = None
    area_range: Optional[AreaRange] = None
    directions: Optional[List[str]] = None
    order: Optional[str] = None
    page: Optional[int] = None


class ComplexAnalysisInput(NaverLandBaseModel):
    complex_no: str
    trade_type: Optional[str] = None
    area_no: Optional[str] = None
    year: Optional[int] = None


class ComparisonInput(NaverLandBaseModel):
    article_nos: List[str] = Field(default_factory=list)


class InvestmentIndicatorInput(NaverLandBaseModel):
    complex_no: Optional[str] = None
    article_no: Optional[str] = None
    trade_type: Optional[str] = None
    area_no: Optional[str] = None


class RawComplexOverview(NaverLandBaseModel):
    complex_no: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("complexNo", "complex_no")
    )
    complex_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("complexName", "complexNm")
    )
    address: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("address", "roadAddress", "roadAddressName"),
    )
    total_household_count: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "totalHouseholdCount", "houseHoldCount", "totalHouseHoldCount"
        ),
    )
    completion_year: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("useApprovalYear", "completionYear")
    )


class RawComplexDetail(NaverLandBaseModel):
    complex_no: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("complexNo", "complex_no")
    )
    complex_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("complexName", "complexNm")
    )
    address: Optional[str] = Field(default=None, validation_alias=AliasChoices("address"))
    total_household_count: Optional[int] = Field(
        default=None,
        validation_alias=AliasChoices(
            "totalHouseholdCount", "houseHoldCount", "totalHouseHoldCount"
        ),
    )
    total_building_count: Optional[int] = Field(
        default=None, validation_alias=AliasChoices("totalBuildingCount")
    )


class RawArticleSummary(NaverLandBaseModel):
    article_no: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("articleNo", "atclNo")
    )
    complex_no: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("complexNo", "complex_no")
    )
    article_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("articleName", "atclNm")
    )
    trade_type: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("tradeType", "tradeTypeCode")
    )
    real_estate_type: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("realEstateType", "realEstateTypeCode")
    )
    price: Optional[str] = None
    deal_price: Optional[str] = Field(default=None, validation_alias=AliasChoices("dealPrice"))
    rent_price: Optional[str] = Field(default=None, validation_alias=AliasChoices("rentPrice"))
    area: Optional[float] = None
    exclusive_area: Optional[float] = Field(
        default=None, validation_alias=AliasChoices("exclusiveArea")
    )
    supply_area: Optional[float] = Field(default=None, validation_alias=AliasChoices("supplyArea"))
    floor_info: Optional[str] = Field(default=None, validation_alias=AliasChoices("floorInfo"))
    direction: Optional[str] = None
    article_feature_description: Optional[str] = Field(
        default=None, alias="atclFetrDesc"
    )


class RawArticleDetail(RawArticleSummary):
    realtor_id: Optional[str] = Field(default=None, validation_alias=AliasChoices("realtorId"))
    realtor_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("realtorName")
    )
    listing_description: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("description", "detailDescription")
    )


class RawSchoolInfo(NaverLandBaseModel):
    school_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("schoolName", "name")
    )
    school_type: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("schoolType", "type")
    )
    distance: Optional[float] = None
    address: Optional[str] = None
    latitude: Optional[float] = Field(default=None, validation_alias=AliasChoices("lat"))
    longitude: Optional[float] = Field(default=None, validation_alias=AliasChoices("lon"))


class RawNeighborhoodInfo(NaverLandBaseModel):
    place_name: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("name", "placeName")
    )
    category: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("category", "type")
    )
    distance: Optional[float] = None
    latitude: Optional[float] = Field(default=None, validation_alias=AliasChoices("lat"))
    longitude: Optional[float] = Field(default=None, validation_alias=AliasChoices("lon"))


class RawPricePoint(NaverLandBaseModel):
    base_date: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("baseDate", "date", "yearMonth")
    )
    price: Optional[float] = None


class RawPriceSummary(NaverLandBaseModel):
    minimum_price: Optional[float] = Field(default=None, validation_alias=AliasChoices("min"))
    maximum_price: Optional[float] = Field(default=None, validation_alias=AliasChoices("max"))
    average_price: Optional[float] = Field(default=None, validation_alias=AliasChoices("avg"))


class RawRealTradeRecord(NaverLandBaseModel):
    trade_date: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("tradeDate", "dealDate", "date")
    )
    price: Optional[float] = None
    area_no: Optional[str] = Field(default=None, validation_alias=AliasChoices("areaNo"))
    floor: Optional[str] = None


class NormalizedArticle(NaverLandBaseModel):
    article_no: Optional[str] = None
    complex_no: Optional[str] = None
    article_name: Optional[str] = None
    trade_type: Optional[str] = None
    real_estate_type: Optional[str] = None
    # 가격은 만원 단위 정수로 통일해 비교/계산 오차를 줄인다.
    price: Optional[int] = None
    rent_price: Optional[int] = None
    area: Optional[float] = None
    exclusive_area: Optional[float] = None
    supply_area: Optional[float] = None
    floor_info: Optional[str] = None
    direction: Optional[str] = None
    article_feature_description: Optional[str] = None


class NormalizedComplex(NaverLandBaseModel):
    complex_no: Optional[str] = None
    complex_name: Optional[str] = None
    address: Optional[str] = None
    total_household_count: Optional[int] = None
    completion_year: Optional[int] = None


class NormalizedSchool(NaverLandBaseModel):
    school_name: Optional[str] = None
    school_type: Optional[str] = None
    distance: Optional[float] = None
    address: Optional[str] = None


class NormalizedTransport(NaverLandBaseModel):
    place_name: Optional[str] = None
    category: Optional[str] = None
    distance: Optional[float] = None


class NormalizedPriceSummary(NaverLandBaseModel):
    minimum_price: Optional[int] = None
    maximum_price: Optional[int] = None
    average_price: Optional[int] = None


class NormalizedRealTradeRecord(NaverLandBaseModel):
    trade_date: Optional[str] = None
    price: Optional[int] = None
    area_no: Optional[str] = None
    floor: Optional[str] = None


class ListingResult(NaverLandBaseModel):
    query_text: Optional[str] = None
    items: List[NormalizedArticle] = Field(default_factory=list)
    sources: List[ApiRequestContext] = Field(default_factory=list)


class ComplexReport(NaverLandBaseModel):
    complex: Optional[NormalizedComplex] = None
    price_summary: Optional[NormalizedPriceSummary] = None
    real_trade_records: List[NormalizedRealTradeRecord] = Field(default_factory=list)
    schools: List[NormalizedSchool] = Field(default_factory=list)
    transports: List[NormalizedTransport] = Field(default_factory=list)
    sources: List[ApiRequestContext] = Field(default_factory=list)


class ComparisonItem(NaverLandBaseModel):
    article: NormalizedArticle
    score: Optional[float] = None
    score_reason: Optional[str] = None


class ComparisonResult(NaverLandBaseModel):
    items: List[ComparisonItem] = Field(default_factory=list)
    recommendation: Optional[str] = None
    sources: List[ApiRequestContext] = Field(default_factory=list)


class InvestmentIndicatorResult(NaverLandBaseModel):
    gap_amount: Optional[int] = None
    yield_rate: Optional[float] = None
    notes: List[str] = Field(default_factory=list)
    sources: List[ApiRequestContext] = Field(default_factory=list)


class HybridReportPayload(NaverLandBaseModel):
    workflow: str
    listing_result: Optional[ListingResult] = None
    complex_report: Optional[ComplexReport] = None
    comparison_result: Optional[ComparisonResult] = None
    investment_indicator_result: Optional[InvestmentIndicatorResult] = None
    generated_at: Optional[str] = None
