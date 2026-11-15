"""The original part of the project: fusing weather + sun data into a score.

Each forecast hour gets a score from 0 to 100:
    temperature (25) + rain (30) + wind (20) + lighting (25)
Weather comes from Open-Meteo. Lighting comes from Sunrise-Sunset.org.
Then we find the best block of consecutive hours for each day.
"""

from datetime import datetime, timedelta

import config

ONE_HOUR = timedelta(hours=1)


# ---------- Scoring rules (one small function per factor) ----------

def score_temperature(temperature, rules):
    low, high = rules["temp_range"]
    if temperature < low:
        gap = low - temperature
    elif temperature > high:
        gap = temperature - high
    else:
        gap = 0
    points = config.MAX_POINTS["temperature"] - config.TEMP_PENALTY_PER_DEGREE * gap
    return max(0.0, points)


def score_rain(rain_probability, rules):
    effective_rain = min(rain_probability * rules["rain_factor"], 100)
    return config.MAX_POINTS["rain"] * (1 - effective_rain / 100)


def score_wind(wind_speed, rules):
    full, zero = rules["wind_full"], rules["wind_zero"]
    maximum = config.MAX_POINTS["wind"]
    if wind_speed <= full:
        return float(maximum)
    if wind_speed >= zero:
        return 0.0
    return maximum * (zero - wind_speed) / (zero - full)


def _inside(moment, period):
    begin, end = period
    return begin is not None and end is not None and begin <= moment < end


def light_points_at(moment, solar, light_mode):
    """Light points for a single moment in time."""
    maximum = config.MAX_POINTS["lighting"]
    is_daylight = solar["sunrise"] <= moment < solar["sunset"]

    if light_mode == "daylight":
        return maximum if is_daylight else 0

    # photography: golden hour > blue hour > ordinary daylight
    if any(_inside(moment, p) for p in solar["golden_hour"].values()):
        return config.PHOTO_LIGHT_POINTS["golden"]
    if any(_inside(moment, p) for p in solar["blue_hour"].values()):
        return config.PHOTO_LIGHT_POINTS["blue"]
    if is_daylight:
        return config.PHOTO_LIGHT_POINTS["daylight"]
    return 0


def cloud_penalty(cloud_cover):
    """Photography: ideal cloud cover is 20-80%."""
    if cloud_cover < 20:
        gap = 20 - cloud_cover
    elif cloud_cover > 80:
        gap = cloud_cover - 80
    else:
        return 0.0
    return config.CLOUD_PENALTY_MAX * gap / 20


def score_lighting(hour_start, solar, rules, cloud_cover):
    """Average the light points over every minute of the hour.

    This way an hour that only partly overlaps daylight (e.g. sunset at 16:51)
    gets partial points instead of all-or-nothing.
    """
    total = 0
    for minute in range(60):
        moment = hour_start + timedelta(minutes=minute)
        total += light_points_at(moment, solar, rules["light_mode"])
    points = total / 60

    if rules["light_mode"] == "photo" and points > 0:
        points = max(0.0, points - cloud_penalty(cloud_cover))
    return points


def score_hour(hour, solar, rules):
    """Score one forecast hour (0-100) with a breakdown by factor."""
    breakdown = {
        "temperature": score_temperature(hour["temperature"], rules),
        "rain": score_rain(hour["rain_probability"], rules),
        "wind": score_wind(hour["wind_speed"], rules),
        "lighting": score_lighting(hour["start"], solar, rules, hour["cloud_cover"]),
    }
    return {
        "start": hour["start"],
        "score": round(sum(breakdown.values()), 1),
        "temperature": hour["temperature"],
        "rain_probability": hour["rain_probability"],
        "wind_speed": hour["wind_speed"],
        "cloud_cover": hour["cloud_cover"],
        "breakdown": {name: round(value, 1) for name, value in breakdown.items()},
    }


# ---------- Finding the best window ----------

def rating_for(score):
    for minimum, label in config.RATINGS:
        if score >= minimum:
            return label
    return config.RATINGS[-1][1]


def find_best_window(scored_hours, size):
    """Best block of consecutive hours (highest average score).

    If no block of the full size exists, we try smaller blocks.
    """
    for current_size in range(min(size, len(scored_hours)), 0, -1):
        best_chunk, best_average = None, -1
        for i in range(len(scored_hours) - current_size + 1):
            chunk = scored_hours[i:i + current_size]
            # make sure the hours really are consecutive (no gaps)
            if chunk[-1]["start"] - chunk[0]["start"] != ONE_HOUR * (current_size - 1):
                continue
            average = sum(h["score"] for h in chunk) / current_size
            if average > best_average:
                best_chunk, best_average = chunk, average
        if best_chunk:
            return best_chunk, best_average
    return None, 0


def _overlapping(start, end, periods):
    """Return the first (begin, end) period that overlaps start..end, or None."""
    for begin, finish in periods.values():
        if begin and finish and start < finish and begin < end:
            return begin, finish
    return None


def explain_window(chunk, solar, rules):
    """Short human-readable reasons for the recommendation."""
    start = chunk[0]["start"]
    end = chunk[-1]["start"] + ONE_HOUR
    count = len(chunk)
    reasons = []

    # Temperature
    average_temp = sum(h["temperature"] for h in chunk) / count
    low, high = rules["temp_range"]
    if low <= average_temp <= high:
        reasons.append(f"Comfortable temperature (about {average_temp:.0f}°C).")
    else:
        reasons.append(f"Temperature is outside the ideal range (about {average_temp:.0f}°C).")

    # Rain
    max_rain = max(h["rain_probability"] for h in chunk)
    if max_rain <= 20:
        reasons.append(f"Low chance of rain (up to {max_rain:.0f}%).")
    elif max_rain <= 50:
        reasons.append(f"Some chance of rain (up to {max_rain:.0f}%).")
    else:
        reasons.append(f"High chance of rain (up to {max_rain:.0f}%).")

    # Wind
    max_wind = max(h["wind_speed"] for h in chunk)
    if max_wind <= rules["wind_full"]:
        reasons.append(f"Light wind (up to {max_wind:.0f} km/h).")
    elif max_wind < rules["wind_zero"]:
        reasons.append(f"Breezy (up to {max_wind:.0f} km/h).")
    else:
        reasons.append(f"Strong wind (up to {max_wind:.0f} km/h).")

    # Light
    golden = _overlapping(start, end, solar["golden_hour"])
    blue = _overlapping(start, end, solar["blue_hour"])
    if rules["light_mode"] == "photo" and golden:
        reasons.append(
            f"Golden hour ({golden[0]:%H:%M}-{golden[1]:%H:%M}) overlaps this window."
        )
    elif rules["light_mode"] == "photo" and blue:
        reasons.append(
            f"Blue hour ({blue[0]:%H:%M}-{blue[1]:%H:%M}) overlaps this window."
        )
    elif solar["sunrise"] <= start and end <= solar["sunset"]:
        reasons.append(f"Full daylight (sunset at {solar['sunset']:%H:%M}).")
    else:
        reasons.append(
            f"Part of this window is outside daylight "
            f"(sunrise {solar['sunrise']:%H:%M}, sunset {solar['sunset']:%H:%M})."
        )
    return reasons


def _window_to_json(chunk, average, solar, rules, label, date_text):
    rating = rating_for(average)
    start = chunk[0]["start"]
    end = chunk[-1]["start"] + ONE_HOUR
    if rating == "Poor":
        summary = f"Not a great time for {label.lower()}."
    else:
        summary = f"{rating} time for {label.lower()}: {start:%H:%M}-{end:%H:%M}."
    return {
        "date": date_text,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "average_score": round(average, 1),
        "rating": rating,
        "summary": summary,
        "reasons": explain_window(chunk, solar, rules),
    }


# ---------- Main function used by the Flask route ----------

def build_recommendation(weather, solar_by_date, activity, now=None):
    """Fuse weather + solar data into the final recommendation (JSON-ready)."""
    rules = config.ACTIVITIES[activity]
    label = rules["label"]
    if now is None:
        now = datetime.now(weather["hours"][0]["start"].tzinfo)

    # Score every hour that has not finished yet, grouped by date
    scored_by_date = {}
    for hour in weather["hours"]:
        if hour["start"] + ONE_HOUR <= now:
            continue
        date_text = hour["start"].date().isoformat()
        solar = solar_by_date[date_text]
        scored_by_date.setdefault(date_text, []).append(score_hour(hour, solar, rules))

    days = []
    best_overall = None
    for date_text in sorted(scored_by_date):
        scored = scored_by_date[date_text]
        solar = solar_by_date[date_text]
        # Only hours with some light can be recommended. Without this, a calm,
        # dry midnight would score 75/100 and look like a "Good" time to go out.
        usable = [h for h in scored if h["breakdown"]["lighting"] > 0]
        chunk, average = find_best_window(usable, config.WINDOW_HOURS)

        window = None
        if chunk:
            window = _window_to_json(chunk, average, solar, rules, label, date_text)
            if best_overall is None or window["average_score"] > best_overall["average_score"]:
                best_overall = window

        hours_json = []
        for item in scored:
            public = {k: v for k, v in item.items() if k != "start"}
            public["time"] = item["start"].isoformat()
            public["has_light"] = item["breakdown"]["lighting"] > 0
            hours_json.append(public)

        days.append({
            "date": date_text,
            "sunrise": solar["sunrise"].isoformat(),
            "sunset": solar["sunset"].isoformat(),
            "best_window": window,
            "note": None if window else "No daylight hours left for this day.",
            "hours": hours_json,
        })

    return {
        "activity": activity,
        "activity_label": label,
        "best_overall": best_overall,
        "days": days,
    }