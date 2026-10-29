"""Test pipeline process exit behavior without external services."""

import unittest
from unittest.mock import patch

from pipeline.run_pipeline import main


class PipelineEntrypointTests(unittest.TestCase):
    @patch("pipeline.run_pipeline.configure_logging")
    @patch("pipeline.run_pipeline.setup_database")
    def test_returns_nonzero_when_fatal_stage_fails(self, setup_database, _configure):
        setup_database.side_effect = RuntimeError("database unavailable")

        with self.assertLogs("pipeline.run_pipeline", level="ERROR"):
            exit_status = main()

        self.assertEqual(exit_status, 1)

    @patch("pipeline.run_pipeline.calculate_and_load_heat_risks")
    @patch("pipeline.run_pipeline.transform_raw_air_quality_to_staging")
    @patch("pipeline.run_pipeline.transform_raw_weather_to_staging")
    @patch("pipeline.run_pipeline.load_air_quality_for_all_locations")
    @patch("pipeline.run_pipeline.load_weather_for_all_locations")
    @patch("pipeline.run_pipeline.setup_database")
    @patch("pipeline.run_pipeline.configure_logging")
    def test_returns_zero_when_all_stages_succeed(
        self,
        _configure,
        setup_database,
        load_weather,
        load_air_quality,
        transform_weather,
        transform_air_quality,
        calculate_risks,
    ):
        exit_status = main()

        self.assertEqual(exit_status, 0)
        setup_database.assert_called_once_with()
        load_weather.assert_called_once_with()
        load_air_quality.assert_called_once_with()
        transform_weather.assert_called_once_with()
        transform_air_quality.assert_called_once_with()
        calculate_risks.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
