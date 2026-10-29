"""Test weather preparation and cleaning."""

import unittest
from datetime import timedelta

from transform.clean_weather import (
    REQUIRED_CURRENT_FIELDS,
    clean_weather_record,
    prepare_raw_weather_record,
)


def valid_weather_data():
    """Return a valid Open-Meteo response."""
    return {
        "current": {
            "time": "2026-10-29T15:00",
            "temperature_2m": "35.2",
            "apparent_temperature": "39.1",
            "relative_humidity_2m": "58",
            "precipitation": "0",
            "wind_speed_10m": "11.4",
        }
    }


class PrepareRawWeatherRecordTests(unittest.TestCase):
    def test_prepares_raw_record_with_karachi_timezone(self):
        weather_data = valid_weather_data()

        result = prepare_raw_weather_record(7, weather_data)

        self.assertEqual(result["location_id"], 7)
        self.assertEqual(result["source_name"], "Open-Meteo")
        self.assertIs(result["api_payload"], weather_data)
        self.assertEqual(result["observed_at"].isoformat(), "2026-10-29T15:00:00+05:00")
        self.assertEqual(result["observed_at"].utcoffset(), timedelta(hours=5))

    def test_rejects_missing_or_empty_current_section(self):
        for weather_data in ({}, {"current": {}}):
            with self.subTest(weather_data=weather_data):
                with self.assertRaisesRegex(ValueError, "does not contain a 'current'"):
                    prepare_raw_weather_record(1, weather_data)

    def test_rejects_each_missing_current_field(self):
        for field in REQUIRED_CURRENT_FIELDS:
            with self.subTest(field=field):
                weather_data = valid_weather_data()
                del weather_data["current"][field]

                with self.assertRaises(ValueError) as context:
                    prepare_raw_weather_record(1, weather_data)

                self.assertIn(field, str(context.exception))

    def test_rejects_invalid_observation_time(self):
        weather_data = valid_weather_data()
        weather_data["current"]["time"] = "invalid"

        with self.assertRaises(ValueError):
            prepare_raw_weather_record(1, weather_data)


class CleanWeatherRecordTests(unittest.TestCase):
    def test_converts_weather_values_for_staging(self):
        weather_data = valid_weather_data()
        raw_record = prepare_raw_weather_record(7, weather_data)
        raw_record["weather_record_id"] = 42

        result = clean_weather_record(raw_record)

        self.assertEqual(
            result,
            {
                "raw_weather_record_id": 42,
                "location_id": 7,
                "observed_at": raw_record["observed_at"],
                "temperature_c": 35.2,
                "apparent_temperature_c": 39.1,
                "humidity_percent": 58,
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 11.4,
            },
        )

    def test_rejects_non_numeric_weather_value(self):
        weather_data = valid_weather_data()
        weather_data["current"]["temperature_2m"] = "invalid"
        raw_record = prepare_raw_weather_record(1, weather_data)
        raw_record["weather_record_id"] = 1

        with self.assertRaises(ValueError):
            clean_weather_record(raw_record)


if __name__ == "__main__":
    unittest.main()
