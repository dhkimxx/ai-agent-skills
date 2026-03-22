import unittest

from scripts.services.article_payload import flatten_article_payload


class TestArticlePayload(unittest.TestCase):
    def test_flatten_article_payload_merges_nested_sections(self) -> None:
        payload = {
            "articleDetail": {"articleNo": "1", "articleName": "테스트 101동"},
            "articleAddition": {"dealOrWarrantPrc": "5억", "floorInfo": "3/20"},
            "articlePrice": {"dealPrice": "5억", "rentPrice": "3억"},
            "articleSpace": {"area1": 104, "area2": 84},
        }

        flattened = flatten_article_payload(payload)

        self.assertEqual(flattened["articleNo"], "1")
        self.assertEqual(flattened["dealPrice"], "5억")
        self.assertEqual(flattened["rentPrice"], "3억")
        self.assertEqual(flattened["area1"], 104)
        self.assertEqual(flattened["area2"], 84)


if __name__ == "__main__":
    unittest.main()
