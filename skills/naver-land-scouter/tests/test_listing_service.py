import unittest

from scripts.schemas import ApiRequestContext, ListingSearchInput
from scripts.services.listing_service import ListingService


class FakeListingRepository:
    def fetch_articles_by_complex(self, complex_no, params):
        return (
            {
                "articleList": [
                    {
                        "articleNo": "1",
                        "articleName": "구성동테스트",
                        "tradeType": "A1",
                        "realEstateType": "APT",
                        "dealPrice": "3억",
                        "area1": 104.0,
                        "area2": 84.0,
                        "floorInfo": "10/20",
                    },
                    {
                        "articleNo": "2",
                        "articleName": "소형테스트",
                        "tradeType": "A1",
                        "realEstateType": "APT",
                        "dealPrice": "2억 8천",
                        "area1": 76.0,
                        "area2": 59.0,
                        "floorInfo": "3/15",
                        "sectionName": "구성동",
                        "lat": 37.2985,
                        "lon": 127.1053,
                    },
                ]
            },
            ApiRequestContext(endpoint="/api/articles/complex/123"),
        )

    def fetch_complex_detail(self, complex_no, params=None):
        return (
            {
                "complexNo": complex_no,
                "address": "경기도 용인시 기흥구 구성동 123",
                "sectionName": "구성동",
                "lat": 37.298958,
                "lon": 127.105713,
            },
            ApiRequestContext(endpoint="/api/complexes/123"),
        )


class TestListingService(unittest.TestCase):
    def test_listing_service_applies_exclusive_area_filter_and_location_fallback(self) -> None:
        service = ListingService(FakeListingRepository())

        result = service.search_by_complex(
            "123",
            ListingSearchInput(
                query_text="manual",
                real_estate_type="APT",
                trade_type="A1",
                exclusive_area_range={"minimum": "25평", "maximum": "35평"},
                center_lat=37.2980,
                center_lon=127.1050,
            ),
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].article_no, "1")
        self.assertEqual(result.items[0].address, "경기도 용인시 기흥구 구성동 123")
        self.assertEqual(result.items[0].dong_name, "구성동")
        self.assertEqual(result.items[0].latitude, 37.298958)
        self.assertEqual(result.items[0].longitude, 127.105713)
        self.assertGreater(result.items[0].distance_meters or 0, 0)
        self.assertEqual(len(result.sources), 2)


if __name__ == "__main__":
    unittest.main()
