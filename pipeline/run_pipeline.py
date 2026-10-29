"""Orchestrate the end-to-end data pipeline."""
"""Run the HeatShield Punjab data pipeline."""

from pathlib import Path
import requests
from config.cities import OPENAQ_LOCATION_IDS
from extract.air_quality_api import (
    fetch_latest_measurements,
    fetch_sensors_for_location,
)
from extract.weather_api import fetch_current_weather
from load.database import get_db_connection
from load.upsert_data import (
    upsert_air_quality_sensor,
    upsert_raw_air_quality_record,
    upsert_raw_weather_record,
    upsert_risk_assessment,
    upsert_staging_weather_record,
)
from transform.clean_weather import (
    clean_weather_record,
    prepare_raw_weather_record,
)
from transform.calculate_risk import calculate_heat_risk


def setup_database():
    """Create initial database tables and seed location data."""
    project_root = Path(__file__).resolve().parents[1]

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for sql_file_name in ("01_create_tables.sql", "02_views.sql"):
                sql_file_path = project_root / "sql" / sql_file_name
                cursor.execute(sql_file_path.read_text(encoding="utf-8"))

        connection.commit()

    print("Database setup completed successfully.")
def get_active_locations():
    """Return all active project locations from PostgreSQL."""
    sql_query = """
        SELECT location_id, city_name, latitude, longitude
        FROM dim_locations
        WHERE is_active = TRUE
        ORDER BY location_id;
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            return cursor.fetchall()


def load_weather_for_all_locations():
    """Fetch and save current weather for every active city."""
    locations = get_active_locations()

    for location_id, city_name, latitude, longitude in locations:
        try:
            weather_data = fetch_current_weather(
                latitude=float(latitude),
                longitude=float(longitude),
            )

            weather_record = prepare_raw_weather_record(
                location_id=location_id,
                weather_data=weather_data,
            )

            weather_record_id = upsert_raw_weather_record(weather_record)

            print(f"{city_name} weather saved. Record ID: {weather_record_id}")

        except requests.RequestException as error:
            print(f"{city_name} weather could not be fetched: {error}")
def get_raw_weather_records():
    """Read all raw weather records from PostgreSQL."""
    sql_query = """
        SELECT
            weather_record_id,
            location_id,
            observed_at,
            api_payload
        FROM raw_weather_data
        ORDER BY weather_record_id;
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()

    return [
        {
            "weather_record_id": row[0],
            "location_id": row[1],
            "observed_at": row[2],
            "api_payload": row[3],
        }
        for row in rows
    ]

def load_air_quality_for_all_locations():
    """Fetch and save current air quality for every active city."""
    locations = get_active_locations()

    for location_id, city_name, _latitude, _longitude in locations:
        openaq_location_id = OPENAQ_LOCATION_IDS.get(city_name)

        if openaq_location_id is None:
            print(f"{city_name} air quality skipped: no verified OpenAQ location.")
            continue

        try:
            measurement_response = fetch_latest_measurements(openaq_location_id)
            sensor_response = fetch_sensors_for_location(openaq_location_id)
            measurements = measurement_response.get("results", [])
            sensors = sensor_response.get("results", [])

            for sensor in sensors:
                upsert_air_quality_sensor(openaq_location_id, sensor)

            for measurement in measurements:
                upsert_raw_air_quality_record(location_id, measurement)

            print(
                f"{city_name} air quality saved: {len(measurements)} measurements, "
                f"{len(sensors)} sensors."
            )
        except requests.RequestException as error:
            print(f"{city_name} air quality could not be fetched: {error}")

def transform_raw_weather_to_staging():
    """Clean raw weather data and save it into the staging table."""
    raw_weather_records = get_raw_weather_records()

    for raw_weather_record in raw_weather_records:
        clean_record = clean_weather_record(raw_weather_record)

        weather_id = upsert_staging_weather_record(clean_record)

        print(
            f"Raw record {raw_weather_record['weather_record_id']} "
            f"cleaned and saved as staging record {weather_id}"
        )
def get_staging_weather_records():
    """Read cleaned weather records ready for risk calculation."""
    sql_query = """
        SELECT
            weather_id,
            location_id,
            apparent_temperature_c
        FROM stg_weather
        ORDER BY weather_id;
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()

    return [
        {
            "weather_id": row[0],
            "location_id": row[1],
            "apparent_temperature_c": row[2],
        }
        for row in rows
    ]


def calculate_and_load_heat_risks():
    """Calculate and save heat risks for cleaned weather records."""
    staging_weather_records = get_staging_weather_records()

    for weather_record in staging_weather_records:
        risk_result = calculate_heat_risk(
            weather_record["apparent_temperature_c"]
        )

        risk_assessment_id = upsert_risk_assessment(
            weather_id=weather_record["weather_id"],
            location_id=weather_record["location_id"],
            risk_result=risk_result,
        )

        print(
            f"Weather record {weather_record['weather_id']} "
            f"saved as risk assessment {risk_assessment_id}: "
            f"{risk_result['heat_risk_level']}"
        )

if __name__ == "__main__":
    try:
        setup_database()
        load_weather_for_all_locations()
        transform_raw_weather_to_staging()
        calculate_and_load_heat_risks()
        get_raw_weather_records()
        load_air_quality_for_all_locations()
        get_staging_weather_records()
    except Exception as error:
        print(f"Pipeline failed: {error}")