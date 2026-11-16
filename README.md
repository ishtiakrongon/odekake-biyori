# ☀️ Odekake Biyori (お出かけ日和)

### Smart Outdoor Activity Planner

**Find your perfect moment outdoors.**

Odekake Biyori is a weather and daylight-based outdoor activity recommendation web application built with **Python, Flask, HTML, CSS, and JavaScript**.

Instead of displaying weather forecasts and sunlight information separately, the application combines data from two public web services to recommend suitable times for outdoor activities.

It evaluates temperature, precipitation probability, wind speed, and natural lighting conditions to identify the best three-hour window for walking, cycling, or photography.

---

## 🌐 Live Demo

**[Launch Odekake Biyori](https://odekake-biyori-planner.vercel.app/)**

**[Explore Interactive API Documentation](https://odekake-biyori-planner.vercel.app/docs)**

**[View OpenAPI Specification](https://odekake-biyori-planner.vercel.app/openapi.yaml)**

The application is deployed on **Vercel** and provides a responsive frontend alongside a RESTful Flask API.

---

## ✨ Features

- **Activity-Based Recommendations:** Choose between walking/sightseeing, cycling, and photography.
- **Multiple Locations:** Explore outdoor conditions in Kyoto, Osaka, and Tokyo.
- **Weather and Solar Data Integration:** Combine hourly weather forecasts with sunrise, sunset, golden-hour, and blue-hour information.
- **Smart Suitability Scoring:** Evaluate outdoor conditions using a custom 100-point scoring algorithm.
- **Best Time Window:** Identify the highest-scoring eligible three-hour period.
- **Interactive Hourly Analysis:** Explore hourly suitability scores and individual scoring factors.
- **Daylight Awareness:** Distinguish nighttime hours from eligible outdoor activity periods.
- **Forecast Selection:** View forecasts covering one to three days.
- **Interactive API Documentation:** Explore and execute requests through Swagger UI.
- **Responsive Design:** A clean interface designed for desktop and mobile browsers.

---

## 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML5, CSS3, JavaScript |
| HTTP Client | Requests |
| Weather Data | Open-Meteo API |
| Solar Data | Sunrise-Sunset.org API v2 |
| API Documentation | OpenAPI 3.0, Swagger UI |
| Dependency Management | uv |
| Hosting | Vercel |
| Version Control | Git, GitHub |

---

## 🔗 External Web Services

### 1. Open-Meteo

[Open-Meteo](https://open-meteo.com/) provides hourly weather forecast information, including:

- Temperature (°C)
- Precipitation probability (%)
- Wind speed (km/h)
- Cloud cover (%)

### 2. Sunrise-Sunset.org

[Sunrise-Sunset.org](https://sunrise-sunset.org/) provides solar-event information, including:

- Sunrise and sunset
- Morning and evening golden hour
- Morning and evening blue hour
- Daylight timing

These two data sources are processed together by the application's recommendation engine.

---

## 🧠 How the Recommendation Engine Works

Odekake Biyori uses an activity-specific scoring algorithm to evaluate weather and lighting conditions.

Every forecast hour receives a suitability score between **0 and 100** based on four factors:

| Scoring Factor | Maximum Points |
|---|---:|
| Temperature | 25 |
| Rain Probability | 30 |
| Wind Speed | 20 |
| Lighting Conditions | 25 |
| **Total** | **100** |

The application follows three main steps:

1. **Retrieve weather data:** Request hourly weather forecasts from Open-Meteo.
2. **Retrieve solar data:** Request sunrise, sunset, golden-hour, and blue-hour information from Sunrise-Sunset.org.
3. **Calculate recommendations:** Combine both datasets, apply activity-specific scoring rules, and evaluate consecutive three-hour windows.

The highest-scoring eligible window is selected as the recommendation.

Different activities use different scoring rules. For example, cycling is more sensitive to rain and wind, while photography benefits from favorable natural lighting, particularly golden hour.

Completely dark hours are excluded from recommended activity windows, although their numerical weather scores may still appear in the hourly visualization.

### Suitability Ratings

| Score | Rating |
|---|---|
| 80–100 | Excellent |
| 65–79 | Good |
| 50–64 | Fair |
| Below 50 | Poor |

*These scores are heuristic estimates intended to assist outdoor planning, not guarantees of weather conditions or personal safety.*

---

## 📡 API Endpoints

The application provides four RESTful API endpoints.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/activities` | Retrieve available activities and scoring factors |
| GET | `/api/weather` | Retrieve normalized hourly weather forecasts |
| GET | `/api/solar` | Retrieve sunrise, sunset, and lighting periods |
| GET | `/api/recommendation` | Generate activity-specific recommendations by combining weather and solar data |

### Example API Request

```http
GET /api/recommendation?activity=photography&days=2
```

**[Try the Recommendation API](https://odekake-biyori-planner.vercel.app/api/recommendation?activity=photography&days=2)**

The response includes the selected activity, location information, source attribution, hourly suitability scores, and the best recommended activity window.

### Interactive Documentation

All four endpoints are documented using **OpenAPI 3.0** and can be tested directly from the browser using Swagger UI.

**[Open Swagger UI](https://odekake-biyori-planner.vercel.app/docs)**

---

## 📁 Project Structure

```text
odekake-biyori/
├── services/
│   ├── __init__.py
│   ├── weather_service.py
│   ├── solar_service.py
│   └── recommendation_service.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── app.py
├── config.py
├── openapi.yaml
├── api-docs.html
├── pyproject.toml
├── uv.lock
└── README.md
```

### Main Components

- **`app.py`** — Flask application, routing, request validation, and API responses.
- **`config.py`** — Application settings, scoring weights, and activity rules.
- **`weather_service.py`** — Open-Meteo integration and weather data normalization.
- **`solar_service.py`** — Sunrise-Sunset.org integration and solar-event processing.
- **`recommendation_service.py`** — Original weather-and-daylight fusion algorithm.
- **`index.html`** — Frontend application structure.
- **`style.css`** — Responsive user interface and visual design system.
- **`app.js`** — API communication, activity controls, and dynamic visualizations.
- **`openapi.yaml`** — Machine-readable REST API specification.
- **`api-docs.html`** — Interactive Swagger UI interface.

---

## 🎨 Design

Odekake Biyori combines a clean, modern dashboard layout with subtle Japanese-inspired visual elements.

The interface follows these design principles:

- Microsoft Fluent-inspired typography
- Structured dashboard layouts
- Natural sage-green and warm neutral colors
- Japanese typography and visual identity
- Accessible controls and interactive data visualizations

The frontend is implemented with **vanilla JavaScript and CSS**, without requiring a frontend framework.

---

## ⚠️ Current Limitations

- Recommendations are based on forecast estimates and custom scoring rules.
- Forecast selection is limited to a maximum of three days.
- The location selector currently provides Kyoto, Osaka, and Tokyo as predefined choices.
- Hourly timezone handling uses a fixed UTC offset, which may not correctly handle daylight-saving time transitions outside Japan.
- The recommendation engine focuses on eligible daylight periods and does not currently support nighttime outdoor activity planning.

Potential future improvements include additional locations, improved timezone handling, customizable activity preferences, and richer weather visualizations.

---

## 🙏 Data Attribution

Weather information is provided by [Open-Meteo](https://open-meteo.com/).

Sunrise, sunset, golden-hour, and blue-hour information is provided by [Sunrise-Sunset.org](https://sunrise-sunset.org/).

---

**Odekake Biyori — Better plans begin with timing.** ☀️