"""Calculate heat and air-quality risk levels."""
"""Calculate heat-risk levels from cleaned weather data."""

from math import isfinite


def calculate_heat_risk(apparent_temperature_c):
    """Return a heat-risk level, score, and practical recommendation."""
    try:
        temperature = float(apparent_temperature_c)
    except (TypeError, ValueError) as error:
        raise ValueError("Apparent temperature must be numeric.") from error

    if not isfinite(temperature):
        raise ValueError("Apparent temperature must be finite.")

    if temperature < 32:
        return {
            "heat_risk_level": "low",
            "heat_risk_score": 1,
            "recommendation": (
                "Low heat risk. Maintain normal hydration during outdoor activity."
            ),
        }

    if temperature < 38:
        return {
            "heat_risk_level": "moderate",
            "heat_risk_score": 2,
            "recommendation": (
                "Moderate heat risk. Drink water regularly and take shade breaks."
            ),
        }

    if temperature < 42:
        return {
            "heat_risk_level": "high",
            "heat_risk_score": 3,
            "recommendation": (
                "High heat risk. Limit prolonged outdoor activity and rest in shade."
            ),
        }

    return {
        "heat_risk_level": "extreme",
        "heat_risk_score": 4,
        "recommendation": (
            "Extreme heat risk. Avoid non-essential outdoor activity where possible."
        ),
    }