import unittest

import httpx

from scripts.naver_land_client import NaverLandApiClient


class TestSessionBootstrap(unittest.TestCase):
    def test_client_bootstraps_http_session_before_first_api_call(self) -> None:
        requests: list[tuple[str, str | None]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.url.path, request.headers.get("cookie")))

            if request.url.path == "/":
                return httpx.Response(
                    200,
                    text="<html></html>",
                    headers={"set-cookie": "REALESTATE=test-state; Path=/; SameSite=Lax"},
                )

            if request.url.path == "/complexes":
                return httpx.Response(
                    200,
                    text="<html></html>",
                    headers=[
                        (
                            "set-cookie",
                            "PROP_TEST_ID=test-id; Domain=.land.naver.com; Path=/; SameSite=Lax",
                        ),
                        (
                            "set-cookie",
                            "PROP_TEST_KEY=test-key; Domain=.land.naver.com; Path=/; SameSite=Lax",
                        ),
                    ],
                )

            if request.url.path == "/api/cortars":
                return httpx.Response(200, json={"cortarNo": "4146311100"})

            raise AssertionError(f"예상하지 못한 요청입니다: {request.url}")

        client = NaverLandApiClient(
            bootstrap_mode="http",
            transport=httpx.MockTransport(handler),
        )

        payload, _ = client.get_json(
            "/api/cortars",
            params={"zoom": 17, "centerLat": 37.269736, "centerLon": 127.075797},
        )
        client.close()

        self.assertEqual(payload["cortarNo"], "4146311100")
        self.assertEqual(requests[0][0], "/")
        self.assertEqual(requests[1][0], "/complexes")
        self.assertEqual(requests[2][0], "/api/cortars")
        self.assertIn("REALESTATE=test-state", requests[2][1] or "")


if __name__ == "__main__":
    unittest.main()
