"""Extract air-quality data from an external API."""
"""Find nearby air-quality monitoring locations with OpenAQ."""

import os

import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = os.getenv("AIR_QUALITY_API_BASE_URL")
API_KEY = os.getenv("OPENAQ_API_KEY")

if not BASE_URL:
    raise ValueError("AIR_QUALITY_API_BASE_URL is missing from .env")

if not API_KEY:
    raise ValueError("OPENAQ_API_KEY is missing from .env")


def find_nearby_monitoring_locations(latitude, longitude):
    """Find OpenAQ monitoring locations within 25 km of a city."""
    headers = {
        "X-API-Key": API_KEY,
    }

    parameters = {
        "coordinates": f"{latitude:.4f},{longitude:.4f}",
        "radius": 25000,
        "limit": 5,
    }

    response = requests.get(
        f"{BASE_URL}/locations",
        headers=headers,
        params=parameters,
        timeout=30,
    )
    response.raise_for_status()

    return response.json()
def fetch_latest_measurements(location_id):
    """Fetch the latest pollutant measurements for one monitoring location."""
    headers = {
        "X-API-Key": API_KEY,
    }

    response = requests.get(
        f"{BASE_URL}/locations/{location_id}/latest",
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    return response.json()
def fetch_sensors_for_location(location_id):
    headers = {
        "X-API-Key": API_KEY,
    }
    res=requests.get(f"{BASE_URL}/locations/{location_id}/sensors", headers=headers, timeout=30)
    res.raise_for_status()
    return res.json()

if __name__ == "__main__":
    location_id = 4755317

    data = fetch_latest_measurements(location_id)
    sensors = fetch_sensors_for_location(location_id)

    print(data)
    print(sensors)