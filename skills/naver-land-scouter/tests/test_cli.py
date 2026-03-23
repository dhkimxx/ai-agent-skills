import json
import tempfile
import unittest
from pathlib import Path

from scripts.cli import _render_report, _write_output_if_requested
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


if __name__ == "__main__":
    unittest.main()
