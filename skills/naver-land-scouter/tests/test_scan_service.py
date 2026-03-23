import unittest

from scripts.schemas import ApiRequestContext, ListingSearchInput, PriceRange
from scripts.services.scan_service import ScanService


class FakeScanRepository:
    def fetch_search(self, params):
        mapping = {
            "기흥역": (37.275664, 127.115956),
            "구성역": (37.299021, 127.105677),
        }
        if params["keyword"] == "죽전역":
            return (
                {
                    "regions": [
                        {
                            "cortarNo": "2729011600",
                            "centerLat": 35.850204,
                            "centerLon": 128.538041,
                            "cortarName": "대구광역시 달서구 죽전동",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=35.850204,128.538041,16&e=RETAIL",
                        }
                    ],
                    "keyword": params["keyword"],
                    "totalCount": 1,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        lat, lon = mapping[params["keyword"]]
        return (
            {
                "deepLink": f"/complexes?ms={lat},{lon},16&e=RETAIL",
                "keyword": params["keyword"],
                "totalCount": 0,
            },
            ApiRequestContext(endpoint="/api/search"),
        )

    def fetch_cortars(self, params):
        return {"cortarNo": "4146311300"}, ApiRequestContext(endpoint="/api/cortars")

    def fetch_complex_markers(self, params):
        center_lon = round((params["leftLon"] + params["rightLon"]) / 2, 6)
        if center_lon < 127.11:
            return (
                [
                    {
                        "markerId": "8107",
                        "complexName": "상떼빌구성역플랫폼시티",
                        "realEstateTypeCode": "APT",
                        "medianDealPrice": 32500,
                        "representativeArea": 81.0,
                        "lat": 37.2992,
                        "lon": 127.1089,
                        "dealCount": 4,
                        "totalArticleCount": 4,
                    }
                ],
                ApiRequestContext(endpoint="/api/complexes/single-markers/2.0"),
            )
        return (
                [
                    {
                        "markerId": "10364",
                        "complexName": "구갈풍림(405-1)",
                        "realEstateTypeCode": "APT",
                        "medianDealPrice": 33000,
                        "representativeArea": 81.0,
                        "lat": 37.275816,
                        "lon": 127.111997,
                        "dealCount": 4,
                        "totalArticleCount": 4,
                    }
                ],
                ApiRequestContext(endpoint="/api/complexes/single-markers/2.0"),
        )

    def fetch_articles_by_complex(self, complex_no, params):
        if complex_no == "10364":
            article_list = [
                {
                    "articleNo": "1",
                    "articleName": "구갈풍림(405-1)",
                    "tradeType": "A1",
                    "realEstateType": "APT",
                    "dealPrice": "3억 2,500",
                    "area1": 81,
                    "area2": 59,
                    "lat": 37.275816,
                    "lon": 127.111997,
                }
            ]
        else:
            article_list = [
                {
                    "articleNo": "2",
                    "articleName": "상떼빌구성역플랫폼시티",
                    "tradeType": "A1",
                    "realEstateType": "APT",
                    "dealPrice": "3억 3,000",
                    "area1": 81,
                    "area2": 59,
                    "lat": 37.2992,
                    "lon": 127.1089,
                }
            ]
        return (
            {"articleList": article_list},
            ApiRequestContext(endpoint=f"/api/articles/complex/{complex_no}"),
        )

    def fetch_complex_detail(self, complex_no, params=None):
        if complex_no == "10364":
            lat, lon, section_name = 37.275816, 127.111997, "구갈동"
        else:
            lat, lon, section_name = 37.2992, 127.1089, "마북동"
        return (
            {
                "complexDetail": {
                    "complexNo": complex_no,
                    "address": "경기도 용인시 기흥구",
                    "sectionName": section_name,
                    "lat": lat,
                    "lon": lon,
                }
            },
            ApiRequestContext(endpoint=f"/api/complexes/{complex_no}"),
        )


class TestScanService(unittest.TestCase):
    def test_scan_near_queries_merges_article_results(self) -> None:
        service = ScanService(FakeScanRepository())

        result = service.scan_near_queries(
            near_queries=["기흥역", "구성역"],
            radius_meters=500,
            real_estate_type="APT",
            listing_input=ListingSearchInput(
                trade_type="A1",
                real_estate_type="APT",
                price_range=PriceRange(minimum=25000, maximum=35000),
            ),
            expand_articles=True,
        )

        self.assertEqual(len(result.targets), 2)
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.filter_stats.before_count, 2)
        self.assertEqual(result.filter_stats.after_count, 2)
        self.assertTrue(all(target.status == "success" for target in result.targets))

    def test_scan_keeps_partial_success_when_one_target_fails(self) -> None:
        service = ScanService(FakeScanRepository())

        result = service.scan_near_queries(
            near_queries=["기흥역", "죽전역"],
            radius_meters=500,
            real_estate_type="APT",
            listing_input=ListingSearchInput(
                trade_type="A1",
                real_estate_type="APT",
                price_range=PriceRange(minimum=25000, maximum=35000),
            ),
            expand_articles=True,
        )

        self.assertEqual(len(result.targets), 2)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.targets[0].status, "success")
        self.assertEqual(result.targets[1].status, "failed")
        self.assertEqual(result.targets[1].error_code, "LOCATION_AMBIGUOUS")
        self.assertTrue(result.warnings)


if __name__ == "__main__":
    unittest.main()
