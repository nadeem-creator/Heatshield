"""Test heat-risk calculation boundaries and validation."""

import unittest
from decimal import Decimal

from transform.calculate_risk import calculate_heat_risk


class CalculateHeatRiskTests(unittest.TestCase):
    def test_assigns_expected_levels_and_scores_at_boundaries(self):
        cases = (
            (31.9, "low", 1),
            (32.0, "moderate", 2),
            (37.9, "moderate", 2),
            (38.0, "high", 3),
            (41.9, "high", 3),
            (42.0, "extreme", 4),
        )

        for temperature, expected_level, expected_score in cases:
            with self.subTest(temperature=temperature):
                result = calculate_heat_risk(temperature)

                self.assertEqual(result["heat_risk_level"], expected_level)
                self.assertEqual(result["heat_risk_score"], expected_score)
                self.assertTrue(result["recommendation"])

    def test_accepts_numeric_strings_and_decimals(self):
        cases = (
            ("31.9", "low"),
            (Decimal("38.0"), "high"),
        )

        for temperature, expected_level in cases:
            with self.subTest(temperature=temperature):
                result = calculate_heat_risk(temperature)

                self.assertEqual(result["heat_risk_level"], expected_level)

    def test_rejects_non_numeric_values(self):
        for temperature in (None, "", "invalid"):
            with self.subTest(temperature=temperature):
                with self.assertRaisesRegex(ValueError, "must be numeric"):
                    calculate_heat_risk(temperature)

    def test_rejects_non_finite_values(self):
        for temperature in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(temperature=temperature):
                with self.assertRaisesRegex(ValueError, "must be finite"):
                    calculate_heat_risk(temperature)


if __name__ == "__main__":
    unittest.main()
