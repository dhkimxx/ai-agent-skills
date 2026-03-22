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
        self.assertIn("총 23건", result.items[0].article_feature_description or "")
        self.assertEqual(repository.marker_params["tradeType"], "")


if __name__ == "__main__":
    unittest.main()
