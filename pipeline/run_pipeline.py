"""Orchestrate the end-to-end data pipeline."""
"""Run the HeatShield Punjab data pipeline."""

from concurrent.futures import ThreadPoolExecutor, as_completed
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
    upsert_staging_air_quality_record,
    upsert_staging_weather_record,
)
from transform.clean_air_quality import clean_air_quality_record
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


def fetch_weather_for_location(location):
    """Fetch and prepare one city's weather record."""
    location_id, city_name, latitude, longitude = location
    weather_data = fetch_current_weather(
        latitude=float(latitude),
        longitude=float(longitude),
    )
    weather_record = prepare_raw_weather_record(
        location_id=location_id,
        weather_data=weather_data,
    )
    return city_name, weather_record


def load_weather_for_all_locations():
    """Fetch and save current weather for every active city."""
    locations = get_active_locations()
    weather_records = []

    if not locations:
        return

    with ThreadPoolExecutor(max_workers=min(3, len(locations))) as executor:
        future_to_city = {
            executor.submit(fetch_weather_for_location, location): location[1]
            for location in locations
        }

        for future in as_completed(future_to_city):
            city_name = future_to_city[future]
            try:
                weather_records.append(future.result())
            except requests.RequestException as error:
                print(f"{city_name} weather could not be fetched: {error}")

    if not weather_records:
        return

    saved_records = []
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for city_name, weather_record in weather_records:
                weather_record_id = upsert_raw_weather_record(cursor, weather_record)
                saved_records.append((city_name, weather_record_id))

    for city_name, weather_record_id in saved_records:
        print(f"{city_name} weather saved. Record ID: {weather_record_id}")
def get_raw_weather_records():
    """Read raw weather records that have not been cleaned."""
    sql_query = """
        SELECT
            raw.weather_record_id,
            raw.location_id,
            raw.observed_at,
            raw.api_payload
        FROM raw_weather_data AS raw
        LEFT JOIN stg_weather AS staging
            ON raw.weather_record_id = staging.raw_weather_record_id
        WHERE staging.weather_id IS NULL
        ORDER BY raw.weather_record_id;
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
    air_quality_batches = []

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

            air_quality_batches.append(
                (location_id, city_name, openaq_location_id, measurements, sensors)
            )
        except requests.RequestException as error:
            print(f"{city_name} air quality could not be fetched: {error}")

    if not air_quality_batches:
        return

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for location_id, _, openaq_location_id, measurements, sensors in air_quality_batches:
                for sensor in sensors:
                    upsert_air_quality_sensor(cursor, openaq_location_id, sensor)

                for measurement in measurements:
                    upsert_raw_air_quality_record(cursor, location_id, measurement)

    for _, city_name, _, measurements, sensors in air_quality_batches:
        print(
            f"{city_name} air quality saved: {len(measurements)} measurements, "
            f"{len(sensors)} sensors."
        )

def get_raw_air_quality_records():
    """Read joined air-quality records that have not been cleaned."""
    sql_query = """
        SELECT
            air.air_quality_record_id,
            air.location_id,
            air.sensor_id,
            air.observed_at,
            air.measurement_value,
            air.parameter_name,
            air.unit,
            air.metadata_found
        FROM vw_air_quality_measurements AS air
        LEFT JOIN stg_air_quality AS staging
            ON air.air_quality_record_id = staging.raw_air_quality_record_id
        WHERE staging.air_quality_id IS NULL
        ORDER BY air.air_quality_record_id;
    """

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()

    return [
        {
            "air_quality_record_id": row[0],
            "location_id": row[1],
            "sensor_id": row[2],
            "observed_at": row[3],
            "measurement_value": row[4],
            "parameter_name": row[5],
            "unit": row[6],
            "metadata_found": row[7],
        }
        for row in rows
    ]


def transform_raw_air_quality_to_staging():
    """Clean raw air-quality data and save valid records to staging."""
    raw_records = get_raw_air_quality_records()
    clean_records = []

    for raw_record in raw_records:
        try:
            clean_records.append(clean_air_quality_record(raw_record))
        except ValueError as error:
            print(
                f"Raw air-quality record {raw_record['air_quality_record_id']} "
                f"rejected: {error}"
            )

    if not clean_records:
        return

    saved_records = []
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for clean_record in clean_records:
                air_quality_id = upsert_staging_air_quality_record(
                    cursor, clean_record
                )
                saved_records.append(
                    (clean_record["raw_air_quality_record_id"], air_quality_id)
                )

    for raw_record_id, air_quality_id in saved_records:
        print(
            f"Raw air-quality record {raw_record_id} "
            f"cleaned and saved as staging record {air_quality_id}"
        )

def transform_raw_weather_to_staging():
    """Clean raw weather data and save it into the staging table."""
    raw_weather_records = get_raw_weather_records()
    clean_records = [
        (raw_weather_record, clean_weather_record(raw_weather_record))
        for raw_weather_record in raw_weather_records
    ]

    if not clean_records:
        return

    saved_records = []

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for raw_weather_record, clean_record in clean_records:
                weather_id = upsert_staging_weather_record(cursor, clean_record)
                saved_records.append((raw_weather_record["weather_record_id"], weather_id))

    for raw_weather_record_id, weather_id in saved_records:
        print(
            f"Raw record {raw_weather_record_id} "
            f"cleaned and saved as staging record {weather_id}"
        )
def get_staging_weather_records():
    """Read cleaned weather records ready for risk calculation."""
    sql_query = """
        SELECT
            weather.weather_id,
            weather.location_id,
            weather.apparent_temperature_c
        FROM stg_weather AS weather
        LEFT JOIN fact_risk_assessments AS risk
            ON weather.weather_id = risk.weather_id
        WHERE risk.risk_assessment_id IS NULL
        ORDER BY weather.weather_id;
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
    risk_records = [
        (weather_record, calculate_heat_risk(weather_record["apparent_temperature_c"]))
        for weather_record in staging_weather_records
    ]

    if not risk_records:
        return

    saved_risks = []

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            for weather_record, risk_result in risk_records:
                risk_assessment_id = upsert_risk_assessment(
                    cursor=cursor,
                    weather_id=weather_record["weather_id"],
                    location_id=weather_record["location_id"],
                    risk_result=risk_result,
                )
                saved_risks.append(
                    (weather_record["weather_id"], risk_assessment_id, risk_result)
                )

    for weather_id, risk_assessment_id, risk_result in saved_risks:
        print(
            f"Weather record {weather_id} "
            f"saved as risk assessment {risk_assessment_id}: "
            f"{risk_result['heat_risk_level']}"
        )

if __name__ == "__main__":
    try:
        setup_database()

        with ThreadPoolExecutor(max_workers=2) as executor:
            weather_future = executor.submit(load_weather_for_all_locations)
            air_quality_future = executor.submit(load_air_quality_for_all_locations)

            weather_future.result()
            air_quality_future.result()

        transform_raw_weather_to_staging()
        transform_raw_air_quality_to_staging()
        calculate_and_load_heat_risks()
    except Exception as error:
        print(f"Pipeline failed: {error}")