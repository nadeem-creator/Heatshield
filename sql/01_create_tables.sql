CREATE TABLE IF NOT EXISTS dim_locations (
    location_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    province VARCHAR(100) NOT NULL DEFAULT 'Punjab',
    latitude NUMERIC(8, 5) NOT NULL,
    longitude NUMERIC(8, 5) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_city_province UNIQUE (city_name, province)
);

INSERT INTO dim_locations (city_name, province, latitude, longitude)
VALUES
    ('Multan', 'Punjab', 30.15750, 71.52490),
    ('Lahore', 'Punjab', 31.52040, 74.35870),
    ('Faisalabad', 'Punjab', 31.45040, 73.13500)
ON CONFLICT (city_name, province) DO NOTHING;
CREATE TABLE IF NOT EXISTS raw_weather_data (
    weather_record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES dim_locations(location_id),
    source_name VARCHAR(100) NOT NULL DEFAULT 'Open-Meteo',
    observed_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    api_payload JSONB NOT NULL,

    CONSTRAINT unique_weather_observation UNIQUE (location_id, observed_at)
);
CREATE TABLE IF NOT EXISTS raw_air_quality_data (
    air_quality_record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES dim_locations(location_id),
    openaq_location_id BIGINT NOT NULL,
    sensor_id BIGINT NOT NULL,
    source_name VARCHAR(100) NOT NULL DEFAULT 'OpenAQ',
    observed_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    api_payload JSONB NOT NULL,

    CONSTRAINT unique_air_quality_observation UNIQUE (sensor_id, observed_at)
);
CREATE TABLE IF NOT EXISTS dim_air_quality_sensors (
    sensor_id BIGINT PRIMARY KEY,
    openaq_location_id BIGINT NOT NULL,
    sensor_name VARCHAR(100) NOT NULL,
    parameter_id BIGINT NOT NULL,
    parameter_name VARCHAR(100) NOT NULL,
    parameter_display_name VARCHAR(100),
    unit VARCHAR(50) NOT NULL,
    metadata_payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS stg_weather (
    weather_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    raw_weather_record_id BIGINT NOT NULL UNIQUE
        REFERENCES raw_weather_data(weather_record_id),
    location_id BIGINT NOT NULL REFERENCES dim_locations(location_id),
    observed_at TIMESTAMPTZ NOT NULL,
    temperature_c NUMERIC(5, 2) NOT NULL,
    apparent_temperature_c NUMERIC(5, 2) NOT NULL,
    humidity_percent INTEGER NOT NULL CHECK (
        humidity_percent BETWEEN 0 AND 100
    ),
    precipitation_mm NUMERIC(6, 2) NOT NULL,
    wind_speed_kmh NUMERIC(6, 2) NOT NULL,
    cleaned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS fact_risk_assessments (
    risk_assessment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    weather_id BIGINT NOT NULL UNIQUE
        REFERENCES stg_weather(weather_id),
    location_id BIGINT NOT NULL
        REFERENCES dim_locations(location_id),
    heat_risk_level VARCHAR(20) NOT NULL,
    heat_risk_score INTEGER NOT NULL CHECK (
        heat_risk_score BETWEEN 1 AND 4
    ),
    recommendation TEXT NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);