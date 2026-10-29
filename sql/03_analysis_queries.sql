SELECT
    location.city_name,
    weather.observed_at,
    weather.temperature_c,
    weather.apparent_temperature_c,
    weather.humidity_percent,
    weather.precipitation_mm,
    weather.wind_speed_kmh
FROM stg_weather AS weather
JOIN dim_locations AS location
    ON weather.location_id = location.location_id
ORDER BY weather.observed_at DESC, location.city_name;

SELECT
    city_name,
    observed_at,
    temperature_c,
    apparent_temperature_c,
    humidity_percent,
    heat_risk_level,
    heat_risk_score,
    recommendation
FROM vw_latest_heat_risk
ORDER BY heat_risk_score DESC, city_name;

SELECT
    city_name,
    parameter_name,
    parameter_display_name,
    measurement_value,
    unit,
    observed_at,
    measurement_age,
    freshness_status
FROM vw_latest_air_quality
WHERE parameter_name IN ('pm1', 'pm25', 'pm10')
ORDER BY city_name, parameter_name;

SELECT
    city_name,
    COUNT(*) AS sensor_count,
    COUNT(*) FILTER (
        WHERE freshness_status = 'fresh'
    ) AS fresh_sensor_count,
    COUNT(*) FILTER (
        WHERE freshness_status = 'stale'
    ) AS stale_sensor_count,
    MAX(observed_at) AS latest_observation
FROM vw_latest_air_quality
GROUP BY city_name
ORDER BY city_name;