CREATE OR REPLACE VIEW vw_latest_heat_risk AS
WITH ranked_weather AS (
    SELECT
        weather.*,
        ROW_NUMBER() OVER (
            PARTITION BY weather.location_id
            ORDER BY weather.observed_at DESC, weather.weather_id DESC
        ) AS row_number
    FROM stg_weather AS weather
)
SELECT
    location.city_name,
    location.province,
    weather.observed_at,
    weather.temperature_c,
    weather.apparent_temperature_c,
    weather.humidity_percent,
    weather.precipitation_mm,
    weather.wind_speed_kmh,
    risk.heat_risk_level,
    risk.heat_risk_score,
    risk.recommendation,
    risk.calculated_at
FROM ranked_weather AS weather
JOIN dim_locations AS location
    ON weather.location_id = location.location_id
JOIN fact_risk_assessments AS risk
    ON weather.weather_id = risk.weather_id
WHERE weather.row_number = 1;

CREATE OR REPLACE VIEW vw_air_quality_measurements AS
SELECT
    measurement.air_quality_record_id,
    location.city_name,
    location.province,
    measurement.openaq_location_id,
    measurement.sensor_id,
    sensor.sensor_name,
    sensor.parameter_id,
    sensor.parameter_name,
    sensor.parameter_display_name,
    measurement.api_payload ->> 'value' AS measurement_value,
    sensor.unit,
    measurement.observed_at,
    measurement.fetched_at,
    sensor.sensor_id IS NOT NULL AS metadata_found,
    measurement.location_id,
    CURRENT_TIMESTAMP - measurement.observed_at AS measurement_age,
    CASE
        WHEN measurement.observed_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
            THEN 'fresh'
        ELSE 'stale'
    END AS freshness_status
FROM raw_air_quality_data AS measurement
JOIN dim_locations AS location
    ON measurement.location_id = location.location_id
LEFT JOIN dim_air_quality_sensors AS sensor
    ON measurement.sensor_id = sensor.sensor_id;

CREATE OR REPLACE VIEW vw_latest_air_quality AS
WITH ranked_air_quality AS (
    SELECT
        air.*,
        ROW_NUMBER() OVER (
            PARTITION BY air.location_id, air.sensor_id
            ORDER BY air.observed_at DESC, air.air_quality_id DESC
        ) AS row_number
    FROM stg_air_quality AS air
)
SELECT
    location.city_name,
    location.province,
    sensor.openaq_location_id,
    air.sensor_id,
    sensor.sensor_name,
    sensor.parameter_id,
    sensor.parameter_name,
    sensor.parameter_display_name,
    air.measurement_value,
    sensor.unit,
    air.observed_at,
    CURRENT_TIMESTAMP - air.observed_at AS measurement_age,
    CASE
        WHEN air.observed_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
            THEN 'fresh'
        ELSE 'stale'
    END AS freshness_status
FROM ranked_air_quality AS air
JOIN dim_locations AS location
    ON air.location_id = location.location_id
JOIN dim_air_quality_sensors AS sensor
    ON air.sensor_id = sensor.sensor_id
WHERE air.row_number = 1;