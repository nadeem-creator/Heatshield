"""Clean and validate extracted air-quality data."""

from datetime import datetime
from decimal import Decimal, InvalidOperation


def clean_air_quality_record(raw_record):
    """Validate one joined OpenAQ record for staging."""
    if not raw_record.get("metadata_found"):
        raise ValueError(
            f"Sensor metadata is missing for sensor {raw_record.get('sensor_id')}."
        )

    required_fields = (
        "air_quality_record_id",
        "location_id",
        "sensor_id",
        "observed_at",
        "measurement_value",
        "parameter_name",
        "unit",
    )
    missing_fields = [
        field for field in required_fields if raw_record.get(field) is None
    ]

    if missing_fields:
        raise ValueError(
            f"Air-quality record is missing fields: {', '.join(missing_fields)}."
        )

    observed_at = raw_record["observed_at"]
    if not isinstance(observed_at, datetime) or observed_at.utcoffset() is None:
        raise ValueError("Air-quality observation timestamp must include a timezone.")

    if not str(raw_record["unit"]).strip():
        raise ValueError("Air-quality measurement unit cannot be empty.")

    try:
        measurement_value = Decimal(str(raw_record["measurement_value"]))
    except InvalidOperation as error:
        raise ValueError("Air-quality measurement value must be numeric.") from error

    if not measurement_value.is_finite():
        raise ValueError("Air-quality measurement value must be finite.")

    return {
        "raw_air_quality_record_id": raw_record["air_quality_record_id"],
        "location_id": raw_record["location_id"],
        "sensor_id": raw_record["sensor_id"],
        "observed_at": observed_at,
        "measurement_value": measurement_value,
    }
