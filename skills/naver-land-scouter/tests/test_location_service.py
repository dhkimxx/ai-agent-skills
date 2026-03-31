import unittest

from scripts.schemas import ApiRequestContext
from scripts.services import ServiceError
from scripts.services.location_service import LocationService


class FakeLocationRepository:
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
        if keyword == "예시동역":
            return (
                {
                    "regions": [
                        {
                            "cortarNo": "3117102000",
                            "centerLat": 35.493193,
                            "centerLon": 129.306038,
                            "cortarName": "예시광역시 예시구 예시읍",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=35.493193,129.306038,16&e=RETAIL",
                        }
                    ],
                    "keyword": keyword,
                    "totalCount": 1,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        if keyword == "예시D역":
            return (
                {
                    "deepLink": "/complexes?ms=35.493193,129.306038,16&e=RETAIL",
                    "keyword": keyword,
                    "totalCount": 0,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        if keyword in {"예시구 예시동", "예시구 예시동2"}:
            return (
                {
                    "regions": [
                        {
                            "cortarNo": "4146510300",
                            "centerLat": 37.341815,
                            "centerLon": 127.098854,
                            "cortarName": "예시광역시 예시구 예시동",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=37.341815,127.098854,16&e=RETAIL",
                        }
                    ],
                    "complexes": [
                        {
                            "complexNo": "8462",
                            "complexName": "예시역센트럴아파트",
                            "latitude": 37.337289,
                            "longitude": 127.096705,
                            "totalHouseholdCount": 344,
                            "totalDongCount": 6,
                            "useApproveYmd": "20040215",
                            "cortarAddress": "예시광역시 예시구 예시동",
                        }
                    ],
                    "keyword": keyword,
                    "totalCount": 1,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        if keyword == "예시구":
            return (
                {
                    "regions": [
                        {
                            "cortarNo": "4146510300",
                            "centerLat": 37.341815,
                            "centerLon": 127.098854,
                            "cortarName": "예시광역시 예시구 예시동",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=37.341815,127.098854,16&e=RETAIL",
                        }
                    ],
                    "keyword": keyword,
                    "totalCount": 1,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        if keyword == "예시동":
            return (
                {
                    "regions": [
                        {
                            "cortarNo": "3020012400",
                            "centerLat": 36.370724,
                            "centerLon": 127.3661,
                            "cortarName": "예시광역시 예시구 예시동A",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=36.370724,127.3661,16&e=RETAIL",
                        },
                        {
                            "cortarNo": "4413110800",
                            "centerLat": 36.797107,
                            "centerLon": 127.170254,
                            "cortarName": "예시광역시 예시구 예시동B",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=36.797107,127.170254,16&e=RETAIL",
                        },
                    ],
                    "keyword": keyword,
                    "totalCount": 2,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        if keyword == "예시검색":
            return (
                {
                    "regions": [
                        {
                            "cortarNo": "3020012400",
                            "centerLat": 36.370724,
                            "centerLon": 127.3661,
                            "cortarName": "예시광역시 예시구 예시동A",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=36.370724,127.3661,16&e=RETAIL",
                        },
                        {
                            "cortarNo": "4413110800",
                            "centerLat": 36.797107,
                            "centerLon": 127.170254,
                            "cortarName": "예시광역시 예시구 예시동B",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=36.797107,127.170254,16&e=RETAIL",
                        },
                        {
                            "cortarNo": "4715041000",
                            "centerLat": 36.032542,
                            "centerLon": 128.047712,
                            "cortarName": "예시광역시 예시면",
                            "cortarType": "sec",
                            "deepLink": "/complexes?ms=36.032542,128.047712,16&e=RETAIL",
                        },
                    ],
                    "keyword": keyword,
                    "totalCount": 3,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        return (
            {
                "regions": [
                    {
                        "cortarNo": "4146510300",
                        "centerLat": 37.341815,
                        "centerLon": 127.098854,
                        "cortarName": "예시광역시 예시구 예시동",
                        "cortarType": "sec",
                        "deepLink": "/complexes?ms=37.341815,127.098854,16&e=RETAIL",
                    }
                ],
                "complexes": [
                    {
                        "complexNo": "10364",
                        "complexName": "예시풍림(405-1)",
                        "latitude": 37.275816,
                        "longitude": 127.111997,
                        "totalHouseholdCount": 180,
                        "totalDongCount": 1,
                        "useApproveYmd": "19960727",
                        "cortarAddress": "예시광역시 예시구 예시동",
                    }
                ],
                "keyword": keyword,
                "totalCount": 0,
            },
            ApiRequestContext(endpoint="/api/search"),
        )

    def fetch_cortars(self, params):
        return {"cortarNo": "4146311300"}, ApiRequestContext(endpoint="/api/cortars")

    def fetch_complex_markers(self, params):
        center_lon = round((params["leftLon"] + params["rightLon"]) / 2, 6)
        if center_lon < 127.1:
            latitude = 37.337289
            longitude = 127.096705
            complex_no = "8462"
            complex_name = "예시역센트럴아파트"
        elif center_lon < 127.11:
            latitude = 37.2992
            longitude = 127.1089
            complex_no = "8107"
            complex_name = "예시역플랫폼시티"
        else:
            latitude = 37.2729
            longitude = 127.1268
            complex_no = "10364"
            complex_name = "예시풍림(405-1)"
        return (
            [
                {
                    "markerId": complex_no,
                    "complexName": complex_name,
                    "realEstateTypeCode": "APT",
                    "medianDealPrice": 32500,
                    "representativeArea": 81.0,
                    "lat": latitude,
                    "lon": longitude,
                    "dealCount": 4,
                    "totalArticleCount": 4,
                }
            ],
            ApiRequestContext(endpoint="/api/complexes/single-markers/2.0"),
        )


class TestLocationService(unittest.TestCase):
    def test_search_prefers_station_query(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("예시역", radius_meters=500, real_estate_type="APT")

        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.query_intent, "station")
        self.assertEqual(result.preferred_candidate.location_type, "station")
        self.assertEqual(result.preferred_candidate.latitude, 37.299021)
        self.assertEqual(result.preferred_candidate.longitude, 127.105677)
        self.assertEqual(len(result.nearby_complexes), 1)

    def test_search_returns_region_and_complex_matches(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("예시구 예시동", radius_meters=500, real_estate_type="APT")

        self.assertEqual(result.query_intent, "region")
        self.assertEqual(result.preferred_candidate.label, "예시광역시 예시구 예시동")
        self.assertEqual(result.complexes[0].complex_name, "예시역센트럴아파트")
        self.assertEqual(result.complexes[0].completion_year, 2004)

    def test_search_marks_same_named_region_query_as_ambiguous(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("예시동", radius_meters=500, real_estate_type="APT")

        self.assertEqual(result.query_intent, "region")
        self.assertIsNone(result.preferred_candidate)
        self.assertEqual(len(result.candidates), 2)
        self.assertEqual(len(result.alternatives), 2)
        self.assertIsNotNone(result.ambiguity_reason)
        self.assertEqual(result.nearby_complexes, [])

    def test_resolve_single_location_rejects_ambiguous_region_query(self) -> None:
        service = LocationService(FakeLocationRepository())

        with self.assertRaises(ServiceError) as captured:
            service.resolve_single_location("예시동")

        self.assertEqual(captured.exception.error_code, "LOCATION_AMBIGUOUS")
        self.assertEqual(captured.exception.details["query_intent"], "region")
        self.assertEqual(len(captured.exception.details["candidates"]), 2)

    def test_search_keeps_generic_query_ambiguous(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("예시검색", radius_meters=500, real_estate_type="APT")

        self.assertEqual(result.query_intent, "unknown")
        self.assertIsNone(result.preferred_candidate)
        self.assertEqual(len(result.candidates), 3)

    def test_search_station_query_rejects_region_only_auto_resolution(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("예시동역", radius_meters=500, real_estate_type="APT")

        self.assertEqual(result.query_intent, "station")
        self.assertIsNone(result.preferred_candidate)
        self.assertEqual(result.candidates[0].location_type, "region")
        self.assertIn("지역 힌트", result.ambiguity_reason)

    def test_search_implicit_region_hint_falls_back_to_region_center(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("예시구 예시C역", radius_meters=700, real_estate_type="APT")

        self.assertEqual(result.query_intent, "station")
        self.assertEqual(result.region_hint, "예시구")
        self.assertEqual(result.resolution_strategy, "region_hint_region_center")
        self.assertEqual(result.preferred_candidate.label, "예시광역시 예시구 예시동")
        self.assertEqual(len(result.nearby_complexes), 1)
        self.assertTrue(result.warnings)

    def test_search_explicit_region_hint_falls_back_to_region_center(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search(
            "예시C역",
            radius_meters=500,
            real_estate_type="APT",
            region_hint="예시구",
        )

        self.assertEqual(result.region_hint, "예시구")
        self.assertEqual(result.resolution_strategy, "region_hint_region_center")
        self.assertEqual(result.preferred_candidate.label, "예시광역시 예시구 예시동")

    def test_search_direct_station_result_is_kept_when_available(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("예시D역", radius_meters=500, real_estate_type="APT")

        self.assertEqual(result.query_intent, "station")
        self.assertEqual(result.preferred_candidate.location_type, "station")
        self.assertEqual(result.resolution_strategy, "direct")


if __name__ == "__main__":
    unittest.main()
