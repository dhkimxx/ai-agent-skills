import json
import tempfile
import unittest
from pathlib import Path

from scripts.cli import _build_output_notice, _render_report, _write_output_if_requested
from scripts.schemas import HybridReportPayload, ListingResult, NormalizedArticle


class TestCliOutput(unittest.TestCase):
    def test_render_report_json(self) -> None:
        payload = HybridReportPayload(
            workflow="listings",
            generated_at="2026-03-23T00:00:00+00:00",
            listing_result=ListingResult(
                query_text="manual",
                items=[
                    NormalizedArticle(
                        article_no="1",
                        article_name="테스트아파트",
                        price=30000,
                    )
                ],
            ),
        )

        rendered = _render_report(payload, "json")
        parsed = json.loads(rendered)

        self.assertEqual(parsed["workflow"], "listings")
        self.assertEqual(parsed["listingResult"]["items"][0]["articleName"], "테스트아파트")

    def test_write_output_if_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "reports" / "result.json"

            _write_output_if_requested(str(output_path), '{"ok": true}')

            self.assertEqual(output_path.read_text(encoding="utf-8"), '{"ok": true}\n')

    def test_build_output_notice(self) -> None:
        payload = HybridReportPayload(
            workflow="listings",
            listing_result=ListingResult(items=[NormalizedArticle(article_no="1")]),
        )

        notice = json.loads(
            _build_output_notice(payload, "/tmp/result.json", "json")
        )

        self.assertEqual(notice["workflow"], "listings")
        self.assertEqual(notice["itemCount"], 1)
        self.assertEqual(notice["outputFile"], "/tmp/result.json")

    def test_render_report_json_for_discover_uses_discovery_result(self) -> None:
        payload = HybridReportPayload(
            workflow="discover",
            generated_at="2026-03-23T00:00:00+00:00",
            discovery_result=ListingResult(
                query_text="discover",
                items=[
                    NormalizedArticle(
                        complex_no="11084",
                        article_name="테스트단지",
                        price=30000,
                    )
                ],
            ),
        )

        rendered = _render_report(payload, "json")
        parsed = json.loads(rendered)

        self.assertEqual(parsed["workflow"], "discover")
        self.assertEqual(parsed["discoveryResult"]["items"][0]["articleName"], "테스트단지")
        self.assertNotIn("listingResult", parsed)

    def test_build_output_notice_for_discover(self) -> None:
        payload = HybridReportPayload(
            workflow="discover",
            discovery_result=ListingResult(items=[NormalizedArticle(article_no="1")]),
        )

        notice = json.loads(
            _build_output_notice(payload, "/tmp/discover.json", "json")
        )

        self.assertEqual(notice["workflow"], "discover")
        self.assertEqual(notice["itemCount"], 1)
        self.assertEqual(notice["outputFile"], "/tmp/discover.json")


if __name__ == "__main__":
    unittest.main()
