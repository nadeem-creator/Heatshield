"""Extract weather data from an external API."""
"""Fetch current weather data from the Open-Meteo API."""

import os
from dotenv import load_dotenv

from extract.http_client import get_json_with_retry


load_dotenv()

BASE_URL = os.getenv("WEATHER_API_BASE_URL")


def fetch_current_weather(latitude, longitude):
    """Fetch current weather for one latitude and longitude."""
    if not BASE_URL:
        raise ValueError("WEATHER_API_BASE_URL is missing from .env")

    parameters = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
        ],
        "timezone": "Asia/Karachi",
    }

    return get_json_with_retry(
        BASE_URL,
        source_name="Open-Meteo",
        params=parameters,
    )


if __name__ == "__main__":
    weather_data = fetch_current_weather(
        latitude=30.15750,
        longitude=71.52490,
    )

    print(weather_data["current"])