import unittest
from datetime import date, timedelta

from scripts.schemas import ApiRequestContext, HistoryInput
from scripts.services.history_service import HistoryService


class FakeHistoryRepository:
    def fetch_article_detail(self, article_no, params=None):
        return (
            {
                "articleDetail": {
                    "articleNo": article_no,
                    "hscpNo": "10364",
                    "ptpNo": "1",
                    "tradeTypeCode": "A1",
                    "aptName": "예시풍림(405-1)",
                    "latitude": "37.275816",
                    "longitude": "127.111997",
                    "sectionName": "예시동",
                },
                "articleAddition": {
                    "dealPrice": 33000,
                    "area1": 81,
                    "area2": 59,
                    "floorInfo": "저/19",
                    "direction": "남향",
                },
            },
            ApiRequestContext(endpoint="/api/articles/2612380492"),
        )

    def fetch_complex_prices(self, complex_no, params):
        today = date.today()
        dates = [
            (today - timedelta(days=100)).isoformat(),
            (today - timedelta(days=200)).isoformat(),
            (today - timedelta(days=500)).isoformat(),
            (today - timedelta(days=1500)).isoformat(),
            (today - timedelta(days=4000)).isoformat(),
        ]
        prices = [30000, 32000, 28000, 25000, 21000]
        floors = [5, 9, 3, 11, 2]
        return (
            {
                "realPriceDataXList": ["rp_x", *dates],
                "realPriceDataYList": ["rp_y", *prices],
                "floorList": floors,
            },
            ApiRequestContext(endpoint="/api/complexes/10364/prices"),
        )


class TestHistoryService(unittest.TestCase):
    def test_create_history_builds_window_summaries_and_premium_summary(self) -> None:
        service = HistoryService(FakeHistoryRepository())

        result = service.create_history(HistoryInput(article_no="2612380492"))

        self.assertEqual(result.article.article_no, "2612380492")
        self.assertEqual(result.article.price, 33000)
        self.assertEqual(result.area_no, "1")
        self.assertEqual(len(result.trade_points), 4)

        summary_by_year = {summary.years: summary for summary in result.window_summaries}
        self.assertEqual(summary_by_year[1].sample_size, 2)
        self.assertEqual(summary_by_year[1].average_price, 31000)
        self.assertEqual(summary_by_year[3].sample_size, 3)
        self.assertEqual(summary_by_year[10].sample_size, 4)

        self.assertEqual(result.premium_summary.primary_window_years, 1)
        self.assertEqual(result.premium_summary.reference_trade_average_price, 31000)
        self.assertEqual(result.premium_summary.premium_amount, 2000)
        self.assertEqual(result.premium_summary.judgement, "premium")


if __name__ == "__main__":
    unittest.main()
