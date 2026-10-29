"""Test air-quality cleaning and validation."""

import unittest
from datetime import datetime, timezone
from decimal import Decimal

from transform.clean_air_quality import clean_air_quality_record


def valid_raw_record():
    """Return a valid joined OpenAQ record."""
    return {
        "air_quality_record_id": 1,
        "location_id": 1,
        "sensor_id": 13339963,
        "observed_at": datetime(2026, 9, 22, 11, tzinfo=timezone.utc),
        "measurement_value": "46.2",
        "parameter_name": "pm25",
        "unit": "µg/m³",
        "metadata_found": True,
    }


class CleanAirQualityRecordTests(unittest.TestCase):
    def test_returns_staging_record_with_decimal_value(self):
        raw_record = valid_raw_record()

        result = clean_air_quality_record(raw_record)

        self.assertEqual(
            result,
            {
                "raw_air_quality_record_id": 1,
                "location_id": 1,
                "sensor_id": 13339963,
                "observed_at": raw_record["observed_at"],
                "measurement_value": Decimal("46.2"),
            },
        )

    def test_accepts_zero_measurement(self):
        raw_record = valid_raw_record()
        raw_record["measurement_value"] = 0

        result = clean_air_quality_record(raw_record)

        self.assertEqual(result["measurement_value"], Decimal("0"))

    def test_rejects_missing_sensor_metadata(self):
        raw_record = valid_raw_record()
        raw_record["metadata_found"] = False

        with self.assertRaisesRegex(ValueError, "Sensor metadata is missing"):
            clean_air_quality_record(raw_record)

    def test_rejects_missing_required_fields(self):
        required_fields = (
            "air_quality_record_id",
            "location_id",
            "sensor_id",
            "observed_at",
            "measurement_value",
            "parameter_name",
            "unit",
        )

        for field in required_fields:
            with self.subTest(field=field):
                raw_record = valid_raw_record()
                raw_record[field] = None

                with self.assertRaisesRegex(ValueError, field):
                    clean_air_quality_record(raw_record)

    def test_rejects_timestamp_without_timezone(self):
        raw_record = valid_raw_record()
        raw_record["observed_at"] = datetime(2026, 9, 22, 11)

        with self.assertRaisesRegex(ValueError, "must include a timezone"):
            clean_air_quality_record(raw_record)

    def test_rejects_empty_unit(self):
        raw_record = valid_raw_record()
        raw_record["unit"] = " "

        with self.assertRaisesRegex(ValueError, "unit cannot be empty"):
            clean_air_quality_record(raw_record)

    def test_rejects_non_numeric_value(self):
        raw_record = valid_raw_record()
        raw_record["measurement_value"] = "invalid"

        with self.assertRaisesRegex(ValueError, "must be numeric"):
            clean_air_quality_record(raw_record)

    def test_rejects_non_finite_values(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value):
                raw_record = valid_raw_record()
                raw_record["measurement_value"] = value

                with self.assertRaisesRegex(ValueError, "must be finite"):
                    clean_air_quality_record(raw_record)


if __name__ == "__main__":
    unittest.main()
