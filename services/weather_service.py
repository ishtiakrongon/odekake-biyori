"""API 1: Open-Meteo (hourly weather)."""

from datetime import datetime, timedelta, timezone

import requests

import config
from services import ExternalServiceError


def get_hourly_weather(latitude, longitude, days=config.DEFAULT_DAYS):
    """Return hourly weather as a clean list.

    Open-Meteo gives times WITHOUT a timezone offset (e.g. "2026-11-15T09:00"),
    but Sunrise-Sunset gives times WITH one (e.g. "...+09:00").
    We use utc_offset_seconds from the response to attach the offset,
    so both APIs can be compared safely.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,cloud_cover",
        "timezone": "auto",
        "forecast_days": days,
    }

    try:
        response = requests.get(
            config.OPEN_METEO_URL, params=params, timeout=config.REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as error:
        raise ExternalServiceError(f"Open-Meteo request failed: {error}")

    try:
        tz = timezone(timedelta(seconds=data["utc_offset_seconds"]))
        hourly = data["hourly"]
        hours = []
        for i, time_text in enumerate(hourly["time"]):
            values = (
                hourly["temperature_2m"][i],
                hourly["precipitation_probability"][i],
                hourly["wind_speed_10m"][i],
                hourly["cloud_cover"][i],
            )
            if any(v is None for v in values):
                continue  # skip hours with missing data
            hours.append(
                {
                    "start": datetime.fromisoformat(time_text).replace(tzinfo=tz),
                    "temperature": values[0],
                    "rain_probability": values[1],
                    "wind_speed": values[2],
                    "cloud_cover": values[3],
                }
            )
        timezone_name = data["timezone"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ExternalServiceError(f"Open-Meteo returned unexpected data: {error}")

    if not hours:
        raise ExternalServiceError("Open-Meteo returned no usable hourly data.")

    return {
        "latitude": data.get("latitude", latitude),
        "longitude": data.get("longitude", longitude),
        "timezone": timezone_name,
        "hours": hours,
    }