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