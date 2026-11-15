"""Settings for Odekake Biyori.

All the numbers that control the recommendation live here,
so they are easy to find, explain in the report, and tune.
"""

# Default location: Kyoto
DEFAULT_LOCATION = {
    "name": "Kyoto",
    "latitude": 35.0116,
    "longitude": 135.7681,
    "timezone": "Asia/Tokyo",
}

# The two public web services we call
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
SUNRISE_SUNSET_URL = "https://api.sunrise-sunset.org/v2"
REQUEST_TIMEOUT = 10  # seconds

# Forecast settings
DEFAULT_DAYS = 2
MAX_DAYS = 3
WINDOW_HOURS = 3  # we recommend a block of this many hours

# Maximum points for each factor (total = 100)
MAX_POINTS = {
    "temperature": 25,
    "rain": 30,
    "wind": 20,
    "lighting": 25,
}

TEMP_PENALTY_PER_DEGREE = 2.5  # points lost per degree outside the ideal range
CLOUD_PENALTY_MAX = 5          # photography only: too clear or too cloudy

# Light points for photography
PHOTO_LIGHT_POINTS = {"golden": 25, "blue": 20, "daylight": 15}

# Activity rules
#   temp_range : ideal temperature range in Celsius
#   rain_factor: how strongly rain chance counts (1.0 = normal)
#   wind_full  : wind speed (km/h) that still gets full points
#   wind_zero  : wind speed (km/h) that gets zero points
#   light_mode : "daylight" = sunrise to sunset, "photo" = golden/blue hour bonus
ACTIVITIES = {
    "walking": {
        "label": "Walking / sightseeing",
        "temp_range": (10, 24),
        "rain_factor": 1.0,
        "wind_full": 15,
        "wind_zero": 40,
        "light_mode": "daylight",
    },
    "cycling": {
        "label": "Cycling",
        "temp_range": (12, 22),
        "rain_factor": 1.5,
        "wind_full": 10,
        "wind_zero": 30,
        "light_mode": "daylight",
    },
    "photography": {
        "label": "Photography",
        "temp_range": (5, 25),
        "rain_factor": 0.8,
        "wind_full": 20,
        "wind_zero": 50,
        "light_mode": "photo",
    },
}

# Score -> rating label (checked from top to bottom)
RATINGS = [
    (80, "Excellent"),
    (65, "Good"),
    (50, "Fair"),
    (0, "Poor"),
]