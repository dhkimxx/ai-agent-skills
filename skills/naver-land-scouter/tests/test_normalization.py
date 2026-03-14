import unittest

from scripts.area_range import parse_area_range, parse_area_range_expression
from scripts.normalization import (
    normalize_area_to_square_meter,
    normalize_price_to_manwon,
)


class TestNormalization(unittest.TestCase):
    def test_normalize_price_to_manwon(self) -> None:
        self.assertEqual(normalize_price_to_manwon("10억"), 100000)
        self.assertEqual(normalize_price_to_manwon("10억 5천"), 105000)
        self.assertEqual(normalize_price_to_manwon("5천만"), 5000)
        self.assertEqual(normalize_price_to_manwon("10억 5천만"), 105000)
        self.assertEqual(normalize_price_to_manwon("5000"), 5000)

    def test_normalize_area_to_square_meter(self) -> None:
        self.assertEqual(normalize_area_to_square_meter("30평"), 99.17)
        self.assertEqual(normalize_area_to_square_meter("84"), 84.0)

    def test_parse_area_range_expression(self) -> None:
        lower, upper = parse_area_range_expression("30~40평")
        self.assertEqual(lower, 99.17)
        self.assertEqual(upper, 132.23)

        lower, upper = parse_area_range_expression("100-120m2")
        self.assertEqual(lower, 100.0)
        self.assertEqual(upper, 120.0)

        lower, upper = parse_area_range_expression("20평대")
        self.assertEqual(lower, 66.12)
        self.assertEqual(upper, 95.87)

        lower, upper = parse_area_range_expression("30 40")
        self.assertEqual(lower, 99.17)
        self.assertEqual(upper, 132.23)

        lower, upper = parse_area_range_expression("100, 120㎡")
        self.assertEqual(lower, 100.0)
        self.assertEqual(upper, 120.0)

    def test_parse_area_range_single(self) -> None:
        lower, upper = parse_area_range("30평")
        self.assertEqual(lower, 99.17)
        self.assertEqual(upper, 99.17)

        lower, upper = parse_area_range("120m2")
        self.assertEqual(lower, 120.0)
        self.assertEqual(upper, 120.0)

        lower, upper = parse_area_range("30")
        self.assertEqual(lower, 99.17)
        self.assertEqual(upper, 99.17)


if __name__ == "__main__":
    unittest.main()
