"""Extract weather data from an external API."""
"""Fetch current weather data from the Open-Meteo API."""

import os
import time
import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = os.getenv("WEATHER_API_BASE_URL")

if not BASE_URL:
    raise ValueError("WEATHER_API_BASE_URL is missing from .env")


def fetch_current_weather(latitude, longitude):
    """Fetch current weather for one latitude and longitude."""
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

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                BASE_URL,
                params=parameters,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as error:
            if attempt == max_attempts:
                raise

            wait_seconds = 2 ** (attempt - 1)

            print(
                f"Weather request failed (attempt {attempt}/{max_attempts}): "
                f"{error}. Retrying in {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
if __name__ == "__main__":
    weather_data = fetch_current_weather(
        latitude=30.15750,
        longitude=71.52490,
    )

    print(weather_data["current"])