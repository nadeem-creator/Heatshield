"""Present HeatShield Punjab measurements in Streamlit."""

import logging
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from load.database import get_db_connection


LOGGER = logging.getLogger(__name__)
POLLUTANT_PARAMETERS = {"pm1", "pm25", "pm10"}
RISK_COLORS = {
    "low": ("#146c43", "#dff7e9"),
    "moderate": ("#8a5a00", "#fff3cd"),
    "high": ("#9a3412", "#ffedd5"),
    "extreme": ("#991b1b", "#fee2e2"),
}


st.set_page_config(
    page_title="HeatShield Punjab",
    page_icon="☀️",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at top right, rgba(249, 115, 22, 0.08), transparent 28rem),
                #f7f8fb;
        }
        .block-container {
            max-width: 1180px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        .hero {
            padding: 2rem 2.2rem;
            border-radius: 22px;
            color: white;
            background: linear-gradient(120deg, #16324f 0%, #176b87 58%, #f97316 140%);
            box-shadow: 0 20px 45px rgba(22, 50, 79, 0.16);
            margin-bottom: 1.4rem;
        }
        .hero h1 {
            margin: 0;
            font-size: clamp(2rem, 5vw, 3.2rem);
            letter-spacing: -0.04em;
        }
        .hero p {
            margin: 0.65rem 0 0;
            max-width: 720px;
            color: rgba(255, 255, 255, 0.82);
            font-size: 1.02rem;
        }
        [data-testid="stMetric"] {
            min-height: 132px;
            padding: 1.15rem 1.25rem;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            color: #0f172a;
            background: rgba(255, 255, 255, 0.92);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p {
            color: #526071;
        }
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] div {
            color: #0f172a;
        }
        .risk-card {
            padding: 1.35rem 1.5rem;
            border-radius: 16px;
            border: 1px solid rgba(15, 23, 42, 0.08);
            margin: 0.25rem 0 1rem;
        }
        .risk-label {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }
        .risk-level {
            margin: 0.25rem 0;
            font-size: 1.7rem;
            font-weight: 750;
            text-transform: capitalize;
        }
        .section-copy {
            color: #667085;
            margin-top: -0.55rem;
            margin-bottom: 1.1rem;
        }
        .footer {
            margin-top: 2.5rem;
            padding-top: 1.2rem;
            border-top: 1px solid #e5e7eb;
            color: #667085;
            font-size: 0.88rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def query_dataframe(sql_query):
    """Return a query result as a pandas DataFrame."""
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=300, show_spinner=False)
def load_dashboard_data():
    """Load dashboard views and recent weather history."""
    heat_risk = query_dataframe(
        """
        SELECT *
        FROM vw_latest_heat_risk
        ORDER BY city_name;
        """
    )
    air_quality = query_dataframe(
        """
        SELECT *
        FROM vw_latest_air_quality
        ORDER BY city_name, parameter_name;
        """
    )
    weather_history = query_dataframe(
        """
        SELECT
            location.city_name,
            weather.observed_at,
            weather.temperature_c,
            weather.apparent_temperature_c,
            weather.humidity_percent,
            weather.wind_speed_kmh
        FROM stg_weather AS weather
        JOIN dim_locations AS location
            ON weather.location_id = location.location_id
        WHERE weather.observed_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
        ORDER BY location.city_name, weather.observed_at;
        """
    )
    return heat_risk, air_quality, weather_history


def format_number(value, suffix="", decimals=1):
    """Format a nullable numeric dashboard value."""
    if pd.isna(value):
        return "Unavailable"
    return f"{float(value):.{decimals}f}{suffix}"


def format_timestamp(value):
    """Format a database timestamp in Pakistan Standard Time."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("Asia/Karachi").strftime("%d %b %Y, %I:%M %p PKT")


def format_age(value):
    """Format a PostgreSQL interval for people."""
    age = pd.Timedelta(value)
    if age.days:
        return f"{age.days} day{'s' if age.days != 1 else ''}"
    hours = max(0, int(age.total_seconds() // 3600))
    return f"{hours} hour{'s' if hours != 1 else ''}"


try:
    with st.spinner("Loading the latest verified measurements..."):
        heat_risk_data, air_quality_data, weather_history_data = load_dashboard_data()
except Exception:
    LOGGER.exception("Dashboard data could not be loaded")
    st.error(
        "The dashboard could not connect to its data source. "
        "Check the database connection and try again."
    )
    st.stop()

cities = sorted(
    set(heat_risk_data.get("city_name", pd.Series(dtype=str)).dropna())
    | set(air_quality_data.get("city_name", pd.Series(dtype=str)).dropna())
)

if not cities:
    st.warning("No processed city data is available yet. Run the pipeline first.")
    st.stop()

with st.sidebar:
    st.title("HeatShield")
    st.caption("Punjab environmental monitoring")
    selected_city = st.selectbox("City", cities)
    if st.button("Refresh data", use_container_width=True):
        load_dashboard_data.clear()
        st.rerun()
    st.divider()
    st.markdown("**Data policy**")
    st.caption(
        "Measurements come from Open-Meteo, OpenAQ, and Neon PostgreSQL. "
        "Air-quality values are shown with their original units."
    )
    st.caption("Fresh means observed within the last 24 hours.")

city_heat = heat_risk_data[heat_risk_data["city_name"] == selected_city]
city_air = air_quality_data[air_quality_data["city_name"] == selected_city].copy()
city_weather_history = weather_history_data[
    weather_history_data["city_name"] == selected_city
].copy()

st.markdown(
    f"""
    <div class="hero">
        <h1>{selected_city}</h1>
        <p>Latest validated weather, heat-risk, and air-quality measurements for Punjab.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if city_heat.empty:
    st.warning("No heat-risk assessment is available for this city.")
else:
    heat = city_heat.iloc[0]
    st.subheader("Weather and heat risk")
    st.markdown(
        '<p class="section-copy">Latest cleaned Open-Meteo observation.</p>',
        unsafe_allow_html=True,
    )
    temperature, feels_like, humidity, wind = st.columns(4)
    temperature.metric(
        "Temperature",
        format_number(heat["temperature_c"], " °C"),
    )
    feels_like.metric(
        "Feels like",
        format_number(heat["apparent_temperature_c"], " °C"),
    )
    humidity.metric(
        "Humidity",
        format_number(heat["humidity_percent"], "%", decimals=0),
    )
    wind.metric(
        "Wind speed",
        format_number(heat["wind_speed_kmh"], " km/h"),
    )

    risk_level = str(heat["heat_risk_level"]).lower()
    risk_color, risk_background = RISK_COLORS.get(
        risk_level,
        ("#334155", "#f1f5f9"),
    )
    st.markdown(
        f"""
        <div class="risk-card" style="color:{risk_color};background:{risk_background}">
            <div class="risk-label">Heat risk · score {int(heat["heat_risk_score"])}/4</div>
            <div class="risk-level">{risk_level}</div>
            <div>{heat["recommendation"]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Weather observed {format_timestamp(heat['observed_at'])}")

st.divider()
st.subheader("Air quality")
st.markdown(
    '<p class="section-copy">Latest validated station readings—not an official AQI.</p>',
    unsafe_allow_html=True,
)

if city_air.empty:
    st.warning("No air-quality measurements are available for this city.")
else:
    stale_rows = city_air[city_air["freshness_status"] == "stale"]
    if not stale_rows.empty:
        oldest_age = stale_rows["measurement_age"].max()
        st.warning(
            f"These station readings are stale ({format_age(oldest_age)} old) "
            "and must not be treated as current conditions."
        )
    else:
        st.success("All displayed station readings were observed within 24 hours.")

    pollutants = city_air[
        city_air["parameter_name"].isin(POLLUTANT_PARAMETERS)
    ].copy()
    if pollutants.empty:
        st.info("No particulate concentration sensors are available for this city.")
    else:
        metric_columns = st.columns(len(pollutants))
        for column, (_, pollutant) in zip(
            metric_columns,
            pollutants.iterrows(),
        ):
            column.metric(
                str(pollutant["parameter_display_name"]),
                format_number(
                    pollutant["measurement_value"],
                    f" {pollutant['unit']}",
                ),
                help=(
                    f"Observed {format_timestamp(pollutant['observed_at'])}; "
                    f"{pollutant['freshness_status']}"
                ),
            )

        particulate_chart = pollutants[
            ["parameter_display_name", "measurement_value"]
        ].copy()
        particulate_chart["measurement_value"] = pd.to_numeric(
            particulate_chart["measurement_value"]
        )
        particulate_chart = particulate_chart.set_index("parameter_display_name")
        st.bar_chart(
            particulate_chart,
            y="measurement_value",
            color="#176b87",
        )
        st.caption(
            "Particulate concentration comparison. Values share µg/m³ units; "
            "particle-count sensors are excluded."
        )

    with st.expander("View all latest sensor readings"):
        sensor_table = city_air[
            [
                "parameter_display_name",
                "measurement_value",
                "unit",
                "observed_at",
                "freshness_status",
            ]
        ].copy()
        sensor_table.columns = [
            "Measurement",
            "Value",
            "Unit",
            "Observed at",
            "Freshness",
        ]
        sensor_table["Observed at"] = sensor_table["Observed at"].map(
            format_timestamp
        )
        st.dataframe(sensor_table, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Recent weather history")
st.markdown(
    '<p class="section-copy">Temperature patterns from cleaned staging records.</p>',
    unsafe_allow_html=True,
)

if city_weather_history.empty:
    st.info("No weather history is available for the last 30 days.")
else:
    city_weather_history["observed_at"] = pd.to_datetime(
        city_weather_history["observed_at"]
    )
    chart_data = city_weather_history[
        ["observed_at", "temperature_c", "apparent_temperature_c"]
    ].rename(
        columns={
            "temperature_c": "Temperature",
            "apparent_temperature_c": "Feels like",
        }
    )
    st.line_chart(
        chart_data,
        x="observed_at",
        y=["Temperature", "Feels like"],
        color=["#176b87", "#f97316"],
    )

st.markdown(
    """
    <div class="footer">
        HeatShield Punjab is a learning and portfolio project. Heat-risk categories
        are project heuristics and air-quality readings are not an official public-health AQI.
    </div>
    """,
    unsafe_allow_html=True,
)