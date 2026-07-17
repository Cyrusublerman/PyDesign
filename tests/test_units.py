from __future__ import annotations

import math
import unittest

from pydesign import Length, cm, inch, mm, pc, pt, px


class UnitTests(unittest.TestCase):
    def test_physical_conversions(self) -> None:
        self.assertAlmostEqual((25.4 * mm).points, inch.points)
        self.assertAlmostEqual((2.54 * cm).points, inch.points)
        self.assertAlmostEqual((6 * pc).points, inch.points)
        self.assertEqual((12 * pt).points, 12.0)
        self.assertAlmostEqual((96 * px).points, inch.points)

    def test_arithmetic_preserves_length(self) -> None:
        result = 10 * mm + 2 * mm - 1 * mm
        self.assertIsInstance(result, Length)
        self.assertAlmostEqual(result.to(mm), 11.0)

    def test_non_finite_length_is_rejected(self) -> None:
        for value in (math.inf, -math.inf, math.nan):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Length(value)


if __name__ == "__main__":
    unittest.main()
