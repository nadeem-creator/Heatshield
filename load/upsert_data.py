"""Upsert transformed data into PostgreSQL."""
"""Insert or update HeatShield Punjab weather data."""

from datetime import datetime

from psycopg.types.json import Jsonb

from load.database import get_db_connection


def upsert_raw_weather_record(weather_record):
    """Save one raw weather record in PostgreSQL."""
    sql_query = """
        INSERT INTO raw_weather_data (
            location_id,
            source_name,
            observed_at,
            api_payload
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (location_id, observed_at)
        DO UPDATE SET
            source_name = EXCLUDED.source_name,
            fetched_at = NOW(),
            api_payload = EXCLUDED.api_payload
        RETURNING weather_record_id;
    """

    values = (
        weather_record["location_id"],
        weather_record["source_name"],
        weather_record["observed_at"],
        Jsonb(weather_record["api_payload"]),
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, values)
            weather_record_id = cursor.fetchone()[0]

        connection.commit()

    return weather_record_id
def upsert_raw_air_quality_record(location_id, measurement):
    """Save one raw OpenAQ measurement in PostgreSQL."""
    sql_query = """
        INSERT INTO raw_air_quality_data (
            location_id,
            openaq_location_id,
            sensor_id,
            observed_at,
            api_payload
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (sensor_id, observed_at)
        DO UPDATE SET
            location_id = EXCLUDED.location_id,
            openaq_location_id = EXCLUDED.openaq_location_id,
            fetched_at = NOW(),
            api_payload = EXCLUDED.api_payload
        RETURNING air_quality_record_id;
    """

    values = (
        location_id,
        measurement["locationsId"],
        measurement["sensorsId"],
        datetime.fromisoformat(measurement["datetime"]["utc"].replace("Z", "+00:00")),
        Jsonb(measurement),
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, values)
            air_quality_record_id = cursor.fetchone()[0]

        connection.commit()

    return air_quality_record_id
def upsert_air_quality_sensor(openaq_location_id, sensor):
    """Save OpenAQ sensor metadata in PostgreSQL."""
    parameter = sensor["parameter"]
    sql_query = """
        INSERT INTO dim_air_quality_sensors (
            sensor_id,
            openaq_location_id,
            sensor_name,
            parameter_id,
            parameter_name,
            parameter_display_name,
            unit,
            metadata_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (sensor_id)
        DO UPDATE SET
            openaq_location_id = EXCLUDED.openaq_location_id,
            sensor_name = EXCLUDED.sensor_name,
            parameter_id = EXCLUDED.parameter_id,
            parameter_name = EXCLUDED.parameter_name,
            parameter_display_name = EXCLUDED.parameter_display_name,
            unit = EXCLUDED.unit,
            metadata_payload = EXCLUDED.metadata_payload,
            updated_at = NOW()
        RETURNING sensor_id;
    """

    values = (
        sensor["id"],
        openaq_location_id,
        sensor["name"],
        parameter["id"],
        parameter["name"],
        parameter.get("displayName"),
        parameter["units"],
        Jsonb(sensor),
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, values)
            sensor_id = cursor.fetchone()[0]

        connection.commit()

    return sensor_id
def upsert_staging_weather_record(clean_weather_record):
    """Save one cleaned weather record in the staging table."""
    sql_query = """
        INSERT INTO stg_weather (
            raw_weather_record_id,
            location_id,
            observed_at,
            temperature_c,
            apparent_temperature_c,
            humidity_percent,
            precipitation_mm,
            wind_speed_kmh
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (raw_weather_record_id)
        DO UPDATE SET
            temperature_c = EXCLUDED.temperature_c,
            apparent_temperature_c = EXCLUDED.apparent_temperature_c,
            humidity_percent = EXCLUDED.humidity_percent,
            precipitation_mm = EXCLUDED.precipitation_mm,
            wind_speed_kmh = EXCLUDED.wind_speed_kmh,
            cleaned_at = NOW()
        RETURNING weather_id;
    """

    values = (
        clean_weather_record["raw_weather_record_id"],
        clean_weather_record["location_id"],
        clean_weather_record["observed_at"],
        clean_weather_record["temperature_c"],
        clean_weather_record["apparent_temperature_c"],
        clean_weather_record["humidity_percent"],
        clean_weather_record["precipitation_mm"],
        clean_weather_record["wind_speed_kmh"],
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, values)
            weather_id = cursor.fetchone()[0]

        connection.commit()

    return weather_id
def upsert_risk_assessment(weather_id, location_id, risk_result):
    """Save one calculated heat-risk assessment."""
    sql_query = """
        INSERT INTO fact_risk_assessments (
            weather_id,
            location_id,
            heat_risk_level,
            heat_risk_score,
            recommendation
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (weather_id)
        DO UPDATE SET
            heat_risk_level = EXCLUDED.heat_risk_level,
            heat_risk_score = EXCLUDED.heat_risk_score,
            recommendation = EXCLUDED.recommendation,
            calculated_at = NOW()
        RETURNING risk_assessment_id;
    """

    values = (
        weather_id,
        location_id,
        risk_result["heat_risk_level"],
        risk_result["heat_risk_score"],
        risk_result["recommendation"],
    )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query, values)
            risk_assessment_id = cursor.fetchone()[0]

        connection.commit()

    return risk_assessment_id