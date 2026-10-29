"""Clean and validate extracted weather data."""
"""Validate and prepare raw weather API responses for database loading."""

from datetime import datetime
from zoneinfo import ZoneInfo


REQUIRED_CURRENT_FIELDS = {
    "time",
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
}


def prepare_raw_weather_record(location_id, weather_data):
    """Validate an API response and prepare one raw database record."""
    current_weather = weather_data.get("current")

    if not current_weather:
        raise ValueError("Weather API response does not contain a 'current' section.")

    missing_fields = REQUIRED_CURRENT_FIELDS - current_weather.keys()

    if missing_fields:
        raise ValueError(f"Weather API response is missing fields: {missing_fields}")

    observed_at = datetime.fromisoformat(current_weather["time"])
    observed_at = observed_at.replace(tzinfo=ZoneInfo("Asia/Karachi"))

    return {
        "location_id": location_id,
        "source_name": "Open-Meteo",
        "observed_at": observed_at,
        "api_payload": weather_data,
    }
def clean_weather_record(raw_weather_record):
    """Convert one raw weather record into clean staging data."""
    current_weather = raw_weather_record["api_payload"]["current"]

    return {
        "raw_weather_record_id": raw_weather_record["weather_record_id"],
        "location_id": raw_weather_record["location_id"],
        "observed_at": raw_weather_record["observed_at"],
        "temperature_c": float(current_weather["temperature_2m"]),
        "apparent_temperature_c": float(
            current_weather["apparent_temperature"]
        ),
        "humidity_percent": int(current_weather["relative_humidity_2m"]),
        "precipitation_mm": float(current_weather["precipitation"]),
        "wind_speed_kmh": float(current_weather["wind_speed_10m"]),
    }