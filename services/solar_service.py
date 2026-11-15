"""API 2: Sunrise-Sunset.org v2 (daylight, golden hour, blue hour)."""

from datetime import datetime

import requests

import config
from services import ExternalServiceError


def _parse_time(value):
    """Turn "2026-11-16T06:31:52+09:00" into an aware datetime (or None)."""
    return datetime.fromisoformat(value) if value else None


def _parse_period(block, name):
    """Read golden_hour/blue_hour -> (begin, end). Missing events become None."""
    period = (block or {}).get(name) or {}
    return (_parse_time(period.get("begin")), _parse_time(period.get("end")))


def get_solar_day(latitude, longitude, timezone_name, date_text=None):
    """Return sun information for one day."""
    params = {"lat": latitude, "lng": longitude, "tz": timezone_name}
    if date_text:
        params["date"] = date_text

    try:
        response = requests.get(
            config.SUNRISE_SUNSET_URL, params=params, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise ExternalServiceError(f"Sunrise-Sunset request failed: {error}")

    # Polar day / polar night: the sun does not rise or set normally.
    if data.get("sun_status", "normal") != "normal":
        raise ExternalServiceError(
            "The sun does not rise and set normally at this location on this date. "
            "Polar locations are not supported yet.",
            status_code=422,
        )

    try:
        return {
            "date": data["date"],
            "sunrise": _parse_time(data["sunrise"]),
            "sunset": _parse_time(data["sunset"]),
            "golden_hour": {
                "morning": _parse_period(data.get("golden_hour"), "morning"),
                "evening": _parse_period(data.get("golden_hour"), "evening"),
            },
            "blue_hour": {
                "morning": _parse_period(data.get("blue_hour"), "morning"),
                "evening": _parse_period(data.get("blue_hour"), "evening"),
            },
        }
    except (KeyError, TypeError, ValueError) as error:
        raise ExternalServiceError(f"Sunrise-Sunset returned unexpected data: {error}")


def period_to_json(period):
    """(begin, end) -> {"begin": "...", "end": "..."} for JSON output."""
    begin, end = period
    return {
        "begin": begin.isoformat() if begin else None,
        "end": end.isoformat() if end else None,
    }


def solar_day_to_json(solar):
    """Convert the datetimes in a solar day dict to ISO text."""
    return {
        "date": solar["date"],
        "sunrise": solar["sunrise"].isoformat(),
        "sunset": solar["sunset"].isoformat(),
        "golden_hour": {k: period_to_json(v) for k, v in solar["golden_hour"].items()},
        "blue_hour": {k: period_to_json(v) for k, v in solar["blue_hour"].items()},
    }