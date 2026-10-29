"""Extract air-quality data from an external API."""
"""Find nearby air-quality monitoring locations with OpenAQ."""

import os

from dotenv import load_dotenv

from extract.http_client import get_json_with_retry


load_dotenv()

BASE_URL = os.getenv("AIR_QUALITY_API_BASE_URL")
API_KEY = os.getenv("OPENAQ_API_KEY")


def _request_headers():
    if not BASE_URL:
        raise ValueError("AIR_QUALITY_API_BASE_URL is missing from .env")
    if not API_KEY:
        raise ValueError("OPENAQ_API_KEY is missing from .env")
    return {"X-API-Key": API_KEY}


def find_nearby_monitoring_locations(latitude, longitude):
    """Find OpenAQ monitoring locations within 25 km of a city."""
    parameters = {
        "coordinates": f"{latitude:.4f},{longitude:.4f}",
        "radius": 25000,
        "limit": 5,
    }

    return get_json_with_retry(
        f"{BASE_URL}/locations",
        source_name="OpenAQ",
        headers=_request_headers(),
        params=parameters,
    )


def fetch_latest_measurements(location_id):
    """Fetch the latest pollutant measurements for one monitoring location."""
    return get_json_with_retry(
        f"{BASE_URL}/locations/{location_id}/latest",
        source_name="OpenAQ",
        headers=_request_headers(),
    )


def fetch_sensors_for_location(location_id):
    """Fetch sensor metadata for one monitoring location."""
    return get_json_with_retry(
        f"{BASE_URL}/locations/{location_id}/sensors",
        source_name="OpenAQ",
        headers=_request_headers(),
    )

if __name__ == "__main__":
    location_id = 4755317

    data = fetch_latest_measurements(location_id)
    sensors = fetch_sensors_for_location(location_id)

    print(data)
    print(sensors)