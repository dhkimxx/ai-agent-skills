import unittest

from scripts.schemas import ApiRequestContext
from scripts.services.location_service import LocationService


class FakeLocationRepository:
    def fetch_search(self, params):
        keyword = params["keyword"]
        if keyword == "구성역":
            return (
                {
                    "deepLink": "/complexes?ms=37.299021,127.105677,16&e=RETAIL",
                    "keyword": keyword,
                    "totalCount": 0,
                },
                ApiRequestContext(endpoint="/api/search"),
            )
        return (
            {
                "regions": [
                    {
                        "cortarNo": "4146310200",
                        "centerLat": 37.272874,
                        "centerLon": 127.127128,
                        "cortarName": "경기도 용인시 기흥구 구갈동",
                        "cortarType": "sec",
                        "deepLink": "/complexes?ms=37.272874,127.127128,16&e=RETAIL",
                    }
                ],
                "complexes": [
                    {
                        "complexNo": "10364",
                        "complexName": "구갈풍림(405-1)",
                        "latitude": 37.275816,
                        "longitude": 127.111997,
                        "totalHouseholdCount": 180,
                        "totalDongCount": 1,
                        "useApproveYmd": "19960727",
                        "cortarAddress": "경기도 용인시 기흥구 구갈동",
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
        if center_lon < 127.11:
            latitude = 37.2992
            longitude = 127.1089
            complex_no = "8107"
            complex_name = "상떼빌구성역플랫폼시티"
        else:
            latitude = 37.2729
            longitude = 127.1268
            complex_no = "10364"
            complex_name = "구갈풍림(405-1)"
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
    def test_search_uses_deep_link_for_landmark_query(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("구성역", radius_meters=500, real_estate_type="APT")

        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].latitude, 37.299021)
        self.assertEqual(result.candidates[0].longitude, 127.105677)
        self.assertEqual(len(result.nearby_complexes), 1)

    def test_search_returns_region_and_complex_matches(self) -> None:
        service = LocationService(FakeLocationRepository())

        result = service.search("구갈동", radius_meters=500, real_estate_type="APT")

        self.assertEqual(result.candidates[0].label, "경기도 용인시 기흥구 구갈동")
        self.assertEqual(result.complexes[0].complex_name, "구갈풍림(405-1)")
        self.assertEqual(result.complexes[0].completion_year, 1996)


if __name__ == "__main__":
    unittest.main()
