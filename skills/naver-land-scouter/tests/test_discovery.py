import unittest

from scripts.param_builder import build_marker_params
from scripts.schemas import ApiRequestContext, BoundingBox
from scripts.services.discovery_service import DiscoveryService


class FakeDiscoveryRepository:
    def __init__(self) -> None:
        self.marker_params = None

    def fetch_cortars(self, params):
        return {"cortarNo": "4146311100"}, ApiRequestContext(endpoint="/api/cortars")

    def fetch_complex_markers(self, params):
        self.marker_params = params
        return (
            [
                {
                    "markerId": "11084",
                    "markerType": "COMPLEX",
                    "complexName": "세종그랑시아",
                    "realEstateTypeCode": "APT",
                    "lat": 37.270736,
                    "lon": 127.076797,
                    "sectionName": "금곡동",
                    "address": "경기도 수원시 권선구 금곡동 111",
                    "medianDealPrice": 67000,
                    "representativeArea": 165.0,
                    "dealCount": 17,
                    "leaseCount": 6,
                    "rentCount": 0,
                    "totalArticleCount": 23,
                }
            ],
            ApiRequestContext(endpoint="/api/complexes/single-markers/2.0"),
        )

    def fetch_complex_overview(self, complex_no):
        return (
            {
                "complexNo": complex_no,
                "complexName": "세종그랑시아",
                "totalHouseHoldCount": 512,
                "useApproveYmd": "20180115",
                "latitude": 37.270736,
                "longitude": 127.076797,
            },
            ApiRequestContext(endpoint=f"/api/complexes/overview/{complex_no}"),
        )

    def fetch_complex_detail(self, complex_no, params=None):
        return (
            {
                "complexDetail": {
                    "complexNo": complex_no,
                    "complexName": "세종그랑시아",
                    "address": "경기도 수원시 권선구 금곡동 111",
                    "parkingPossibleCount": 600,
                    "totalDongCount": 8,
                    "totalHouseholdCount": 512,
                    "useApproveYmd": "20180115",
                    "latitude": 37.270736,
                    "longitude": 127.076797,
                }
            },
            ApiRequestContext(endpoint=f"/api/complexes/{complex_no}"),
        )


class TestDiscovery(unittest.TestCase):
    def test_build_marker_params_keeps_browser_default_keys(self) -> None:
        params = build_marker_params(
            cortar_no="4146311100",
            bounding_box=BoundingBox(
                left_lon=127.0,
                right_lon=128.0,
                top_lat=37.3,
                bottom_lat=37.2,
            ),
            zoom=17,
            real_estate_type="APT:ABYG:JGC:PRE",
        )

        self.assertEqual(params["priceType"], "RETAIL")
        self.assertEqual(params["tag"], "::::::::")
        self.assertEqual(params["tradeType"], "")
        self.assertEqual(params["markerId"], "")
        self.assertFalse(params["showArticle"])
        self.assertFalse(params["sameAddressGroup"])

    def test_discovery_service_extracts_marker_summary(self) -> None:
        repository = FakeDiscoveryRepository()
        service = DiscoveryService(repository)

        result = service.discover_by_map(
            center_lat=37.269736,
            center_lon=127.075797,
            zoom=17,
            bounding_box=BoundingBox(
                left_lon=127.0689305,
                right_lon=127.0826635,
                top_lat=37.2731041,
                bottom_lat=37.2663677,
            ),
            real_estate_type="APT:ABYG:JGC:PRE",
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].complex_no, "11084")
        self.assertEqual(result.items[0].article_name, "세종그랑시아")
        self.assertEqual(result.items[0].price, 67000)
        self.assertEqual(result.items[0].exclusive_area, 165.0)
        self.assertEqual(result.items[0].dong_name, "금곡동")
        self.assertEqual(result.items[0].latitude, 37.270736)
        self.assertEqual(result.items[0].longitude, 127.076797)
        self.assertEqual(result.items[0].address, "경기도 수원시 권선구 금곡동 111")
        self.assertGreater(result.items[0].distance_meters or 0, 0)
        self.assertIn("총 23건", result.items[0].article_feature_description or "")
        self.assertEqual(repository.marker_params["tradeType"], "")

    def test_discovery_service_enriches_complex_summary(self) -> None:
        repository = FakeDiscoveryRepository()
        service = DiscoveryService(repository)

        result = service.discover_by_map(
            center_lat=37.269736,
            center_lon=127.075797,
            zoom=17,
            bounding_box=BoundingBox(
                left_lon=127.0689305,
                right_lon=127.0826635,
                top_lat=37.2731041,
                bottom_lat=37.2663677,
            ),
            real_estate_type="APT:ABYG:JGC:PRE",
            enrich_mode="complex-summary",
        )

        self.assertEqual(result.items[0].total_household_count, 512)
        self.assertEqual(result.items[0].total_building_count, 8)
        self.assertEqual(result.items[0].completion_year, 2018)
        self.assertEqual(result.items[0].parking_count, 600)

    def test_discovery_service_applies_radius_filter(self) -> None:
        class RadiusRepository(FakeDiscoveryRepository):
            def fetch_complex_markers(self, params):
                return (
                    [
                        {
                            "markerId": "1",
                            "complexName": "가까운단지",
                            "realEstateTypeCode": "APT",
                            "medianDealPrice": 50000,
                            "representativeArea": 84.0,
                            "lat": 37.2699,
                            "lon": 127.0761,
                        },
                        {
                            "markerId": "2",
                            "complexName": "먼단지",
                            "realEstateTypeCode": "APT",
                            "medianDealPrice": 50000,
                            "representativeArea": 84.0,
                            "lat": 37.2760,
                            "lon": 127.0850,
                        },
                    ],
                    ApiRequestContext(endpoint="/api/complexes/single-markers/2.0"),
                )

        service = DiscoveryService(RadiusRepository())
        result = service.discover_by_map(
            center_lat=37.269736,
            center_lon=127.075797,
            zoom=17,
            bounding_box=BoundingBox(
                left_lon=127.0689305,
                right_lon=127.0826635,
                top_lat=37.2731041,
                bottom_lat=37.2663677,
            ),
            real_estate_type="APT:ABYG:JGC:PRE",
            radius_meters=500,
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].article_name, "가까운단지")
        self.assertEqual(result.filter_stats.before_count, 2)
        self.assertEqual(result.filter_stats.after_count, 1)


if __name__ == "__main__":
    unittest.main()
