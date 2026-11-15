"""Odekake Biyori (お出かけ日和) - Kyoto Outdoor Activity Planner.

A Flask web service that calls two public web services:
  1. Open-Meteo        -> hourly weather
  2. Sunrise-Sunset.org -> daylight, golden hour, blue hour
and fuses them into an activity suitability score.
"""

from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory

import config
from services import ExternalServiceError
from services.recommendation_service import build_recommendation
from services.solar_service import get_solar_day, solar_day_to_json
from services.weather_service import get_hourly_weather

app = Flask(__name__)

ATTRIBUTION = [
    {"name": "Open-Meteo.com", "url": "https://open-meteo.com/"},
    {"name": "Sunrise-Sunset.org", "url": "https://sunrise-sunset.org/"},
]


# ---------- Input helpers ----------

class InputError(Exception):
    """The caller sent something invalid (HTTP 400)."""


def read_number(name, default, low, high):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        raise InputError(f"'{name}' must be a number.")
    if not low <= value <= high:
        raise InputError(f"'{name}' must be between {low} and {high}.")
    return value


def read_location():
    latitude = read_number("lat", config.DEFAULT_LOCATION["latitude"], -90, 90)
    longitude = read_number("lng", config.DEFAULT_LOCATION["longitude"], -180, 180)
    return latitude, longitude


def read_days():
    raw = request.args.get("days")
    if raw is None or raw == "":
        return config.DEFAULT_DAYS
    try:
        days = int(raw)
    except ValueError:
        raise InputError("'days' must be a whole number.")
    if not 1 <= days <= config.MAX_DAYS:
        raise InputError(f"'days' must be between 1 and {config.MAX_DAYS}.")
    return days


def read_activity():
    activity = request.args.get("activity", "walking").lower()
    if activity not in config.ACTIVITIES:
        choices = ", ".join(config.ACTIVITIES)
        raise InputError(f"Unknown activity '{activity}'. Choose one of: {choices}.")
    return activity


# ---------- Error handlers (always return JSON) ----------

@app.errorhandler(InputError)
def handle_input_error(error):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(ExternalServiceError)
def handle_external_error(error):
    return jsonify({"error": error.message}), error.status_code


# ---------- Routes ----------

@app.route("/")
def index():
    return render_template("index.html", default_location=config.DEFAULT_LOCATION)


@app.route("/api/activities")
def activities():
    """List the activities and the maximum points of each scoring factor."""
    return jsonify({
        "activities": [
            {"id": key, "label": rules["label"]}
            for key, rules in config.ACTIVITIES.items()
        ],
        "max_points": config.MAX_POINTS,
    })


@app.route("/api/weather")
def weather():
    """API 1 only: hourly weather from Open-Meteo."""
    latitude, longitude = read_location()
    data = get_hourly_weather(latitude, longitude, read_days())
    hours = [
        {**{k: v for k, v in hour.items() if k != "start"}, "time": hour["start"].isoformat()}
        for hour in data["hours"]
    ]
    return jsonify({
        "latitude": data["latitude"],
        "longitude": data["longitude"],
        "timezone": data["timezone"],
        "hours": hours,
        "attribution": ATTRIBUTION[0],
    })


@app.route("/api/solar")
def solar():
    """API 2 only: sun information from Sunrise-Sunset.org."""
    latitude, longitude = read_location()
    timezone_name = request.args.get("tz")
    if timezone_name is None:
        if "lat" in request.args or "lng" in request.args:
            raise InputError("'tz' is required (for example Asia/Tokyo) when you pass your own coordinates.")
        timezone_name = config.DEFAULT_LOCATION["timezone"]
    date_text = request.args.get("date")
    if date_text:
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            raise InputError("'date' must look like YYYY-MM-DD.")
    day = get_solar_day(latitude, longitude, timezone_name, date_text)
    result = solar_day_to_json(day)
    result["attribution"] = ATTRIBUTION[1]
    return jsonify(result)


@app.route("/api/recommendation")
def recommendation():
    """Both APIs fused: score every hour and recommend the best time window."""
    latitude, longitude = read_location()
    activity = read_activity()
    days = read_days()

    # Step 1: weather (API 1). It also tells us the local timezone.
    weather_data = get_hourly_weather(latitude, longitude, days)

    # Step 2: sun data (API 2), one call per date in the forecast
    dates = sorted({hour["start"].date().isoformat() for hour in weather_data["hours"]})
    solar_by_date = {
        date_text: get_solar_day(latitude, longitude, weather_data["timezone"], date_text)
        for date_text in dates
    }

    # Step 3: fuse the two sources into one recommendation
    result = build_recommendation(weather_data, solar_by_date, activity)
    result["location"] = {
        "name": config.DEFAULT_LOCATION["name"]
        if "lat" not in request.args and "lng" not in request.args
        else None,
        "latitude": weather_data["latitude"],
        "longitude": weather_data["longitude"],
        "timezone": weather_data["timezone"],
    }
    result["attribution"] = ATTRIBUTION
    return jsonify(result)

@app.get("/docs")
@app.get("/api-docs.html")
def api_docs():
    """Serve interactive Swagger UI documentation."""
    return send_from_directory(app.root_path, "api-docs.html")


@app.get("/openapi.yaml")
def openapi_spec():
    """Serve the OpenAPI specification used by Swagger UI."""
    return send_from_directory(
        app.root_path, "openapi.yaml", mimetype="application/yaml"
    )

if __name__ == "__main__":
    app.run(debug=True)