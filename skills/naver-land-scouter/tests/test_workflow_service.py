import unittest

from scripts.schemas import ApiRequestContext, AreaRange, ListingSearchInput, PriceRange
from scripts.services.workflow_service import WorkflowService

ARTICLE_PRICE = 32500
ARTICLE_SUPPLY_AREA = 81.0
ARTICLE_EXCLUSIVE_AREA = 59.0
ARTICLE_LATITUDE = 37.304621
ARTICLE_LONGITUDE = 127.105677
COMPLEX_NO = "8107"
ARTICLE_NO = "2612380492"


class FakeWorkflowRepository:
    def fetch_search(self, params):
        keyword = params["keyword"]
        if keyword == "예시역":
            return (
                {
                    "deepLink": "/complexes?ms=37.299021,127.105677,16&e=RETAIL",
                    "keyword": keyword,
                    "totalCount": 0,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        raise AssertionError(f"unexpected keyword: {keyword}")

    def fetch_cortars(self, params):
        return {"cortarNo": "4146311300"}, ApiRequestContext(endpoint="/api/cortars")

    def fetch_complex_markers(self, params):
        return (
            [
                {
                    "markerId": COMPLEX_NO,
                    "complexName": "예시역플랫폼시티",
                    "realEstateTypeCode": "APT",
                    "medianDealPrice": ARTICLE_PRICE,
                    "representativeArea": ARTICLE_SUPPLY_AREA,
                    "lat": ARTICLE_LATITUDE,
                    "lon": ARTICLE_LONGITUDE,
                    "dealCount": 4,
                    "totalArticleCount": 4,
                }
            ],
            ApiRequestContext(endpoint="/api/complexes/single-markers/2.0"),
        )

    def fetch_articles_by_complex(self, complex_no, params):
        if not _matches_price_range(params):
            article_list = []
        elif not _matches_area_range(params):
            article_list = []
        else:
            article_list = [
                {
                    "articleNo": ARTICLE_NO,
                    "complexNo": complex_no,
                    "articleName": "예시역플랫폼시티",
                    "tradeType": "A1",
                    "realEstateType": "APT",
                    "dealPrice": "3억 2,500",
                    "area1": ARTICLE_SUPPLY_AREA,
                    "area2": ARTICLE_EXCLUSIVE_AREA,
                    "lat": ARTICLE_LATITUDE,
                    "lon": ARTICLE_LONGITUDE,
                }
            ]
        return (
            {"articleList": article_list},
            ApiRequestContext(endpoint=f"/api/articles/complex/{complex_no}"),
        )

    def fetch_complex_detail(self, complex_no, params=None):
        return (
            {
                "complexDetail": {
                    "complexNo": complex_no,
                    "address": "예시광역시 예시구 예시동",
                    "sectionName": "예시동",
                    "lat": ARTICLE_LATITUDE,
                    "lon": ARTICLE_LONGITUDE,
                }
            },
            ApiRequestContext(endpoint=f"/api/complexes/{complex_no}"),
        )

    def fetch_article_detail(self, article_no, params=None):
        return (
            {
                "articleDetail": {
                    "articleNo": article_no,
                    "complexNo": COMPLEX_NO,
                    "articleName": "예시역플랫폼시티",
                    "tradeType": "A1",
                    "realEstateType": "APT",
                    "dealOrWarrantPrc": ARTICLE_PRICE,
                    "sectionName": "예시동",
                    "exposureAddress": "예시광역시 예시구 예시동",
                    "latitude": ARTICLE_LATITUDE,
                    "longitude": ARTICLE_LONGITUDE,
                    "areaNo": "1",
                },
                "articleSpace": {
                    "supplySpace": ARTICLE_SUPPLY_AREA,
                    "exclusiveSpace": ARTICLE_EXCLUSIVE_AREA,
                },
            },
            ApiRequestContext(endpoint=f"/api/articles/{article_no}"),
        )

    def fetch_complex_prices(self, complex_no, params):
        return (
            {
                "realPriceDataXList": [
                    "date",
                    "2026-02-01",
                    "2025-10-01",
                    "2025-06-01",
                ],
                "realPriceDataYList": [
                    "price",
                    32000,
                    31800,
                    32100,
                ],
                "floorList": ["7", "9", "11"],
            },
            ApiRequestContext(endpoint=f"/api/complexes/{complex_no}/prices"),
        )


class TestWorkflowService(unittest.TestCase):
    def test_workflow_relaxes_radius_until_results_exist(self) -> None:
        service = WorkflowService(FakeWorkflowRepository())

        result = service.run_listing_workflow(
            near_queries=["예시역"],
            radius_meters=500,
            fallback_radius_meters=[700, 1000],
            real_estate_type="APT",
            listing_input=ListingSearchInput(
                trade_type="A1",
                real_estate_type="APT",
                price_range=PriceRange(minimum=25000, maximum=35000),
            ),
            expand_articles=True,
            recommend_limit=3,
            history_enrich_limit=1,
        )

        self.assertEqual(result.completion_status, "success")
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[0].completion_status, "no_results")
        self.assertEqual(result.attempts[1].relaxation_stage, "radius_relaxed")
        self.assertTrue(result.attempts[1].selected)
        self.assertEqual(result.final_radius_meters, 700)
        self.assertEqual(len(result.recommended_items), 1)
        self.assertIn("700m", result.selected_reason)
        self.assertIsNotNone(result.recommended_items[0].premium_summary)

    def test_workflow_relaxes_price_when_radius_attempts_are_exhausted(self) -> None:
        service = WorkflowService(FakeWorkflowRepository())

        result = service.run_listing_workflow(
            near_queries=["예시역"],
            radius_meters=700,
            fallback_radius_meters=[],
            real_estate_type="APT",
            listing_input=ListingSearchInput(
                trade_type="A1",
                real_estate_type="APT",
                price_range=PriceRange(minimum=30000, maximum=31000),
            ),
            expand_articles=True,
            recommend_limit=3,
            history_enrich_limit=0,
        )

        self.assertEqual(result.completion_status, "success")
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[1].relaxation_stage, "price_relaxed")
        self.assertTrue(result.attempts[1].selected)
        self.assertEqual(result.recommended_items[0].price, ARTICLE_PRICE)

    def test_workflow_relaxes_supply_area_when_needed(self) -> None:
        service = WorkflowService(FakeWorkflowRepository())

        result = service.run_listing_workflow(
            near_queries=["예시역"],
            radius_meters=700,
            fallback_radius_meters=[],
            real_estate_type="APT",
            listing_input=ListingSearchInput(
                trade_type="A1",
                real_estate_type="APT",
                area_range=AreaRange(minimum="20평", maximum="20평"),
            ),
            expand_articles=True,
            recommend_limit=3,
            history_enrich_limit=0,
        )

        self.assertEqual(result.completion_status, "success")
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[1].relaxation_stage, "supply_area_relaxed")
        self.assertTrue(result.attempts[1].selected)
        self.assertIn("공급면적", result.selected_reason)

    def test_workflow_enriches_recommended_items_with_premium_summary(self) -> None:
        service = WorkflowService(FakeWorkflowRepository())

        result = service.run_listing_workflow(
            near_queries=["예시역"],
            radius_meters=700,
            fallback_radius_meters=[],
            real_estate_type="APT",
            listing_input=ListingSearchInput(
                trade_type="A1",
                real_estate_type="APT",
                price_range=PriceRange(minimum=25000, maximum=35000),
            ),
            expand_articles=True,
            recommend_limit=3,
            history_enrich_limit=1,
        )

        self.assertEqual(result.completion_status, "success")
        self.assertEqual(len(result.recommended_items), 1)
        premium_summary = result.recommended_items[0].premium_summary
        self.assertIsNotNone(premium_summary)
        self.assertEqual(premium_summary.primary_window_years, 1)
        self.assertEqual(premium_summary.current_asking_price, ARTICLE_PRICE)
        self.assertEqual(premium_summary.judgement, "fair")

    def test_workflow_returns_next_actions_when_all_attempts_empty(self) -> None:
        service = WorkflowService(FakeWorkflowRepository())

        result = service.run_listing_workflow(
            near_queries=["예시역"],
            radius_meters=500,
            fallback_radius_meters=[700],
            real_estate_type="APT",
            listing_input=ListingSearchInput(
                trade_type="A1",
                real_estate_type="APT",
                price_range=PriceRange(minimum=1000, maximum=2000),
            ),
            expand_articles=True,
            recommend_limit=3,
            history_enrich_limit=0,
        )

        self.assertEqual(result.completion_status, "no_results")
        self.assertEqual(result.final_radius_meters, 700)
        self.assertEqual(len(result.recommended_items), 0)
        self.assertEqual(len(result.attempts), 3)
        self.assertEqual(result.attempts[-1].relaxation_stage, "price_relaxed")
        self.assertTrue(result.next_actions)


def _matches_price_range(params) -> bool:
    price_min = params.get("priceMin")
    price_max = params.get("priceMax")
    if price_min is not None and ARTICLE_PRICE < price_min:
        return False
    if price_max is not None and ARTICLE_PRICE > price_max:
        return False
    return True



def _matches_area_range(params) -> bool:
    area_min = params.get("areaMin")
    area_max = params.get("areaMax")
    if area_min is not None and ARTICLE_SUPPLY_AREA < float(area_min):
        return False
    if area_max is not None and ARTICLE_SUPPLY_AREA > float(area_max):
        return False
    return True


if __name__ == "__main__":
    unittest.main()
