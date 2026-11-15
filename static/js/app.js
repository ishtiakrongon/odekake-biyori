
"use strict";

/*
 * Odekake Biyori — frontend controller
 * No libraries. All forecast data comes from the Flask API.

 */

const LOCATIONS = Object.freeze({
  kyoto: { name: "Kyoto", latitude: 35.0116, longitude: 135.7681 },
  osaka: { name: "Osaka", latitude: 34.6937, longitude: 135.5023 },
  tokyo: { name: "Tokyo", latitude: 35.6762, longitude: 139.6503 },
});

const FACTORS = [
  { key: "temperature", label: "Temperature" },
  { key: "rain", label: "Rain chance" },
  { key: "wind", label: "Wind" },
  { key: "lighting", label: "Lighting" },
];

const state = {
  location: "kyoto",
  activity: "walking",
  days: 2,
  maxPoints: { temperature: 25, rain: 30, wind: 20, lighting: 25 },
  requestId: 0,
  abortController: null,
};

const answerBox = document.getElementById("answer");
const daysBox = document.getElementById("days");
const activityButtons = document.getElementById("activity-buttons");
const dayButtons = document.getElementById("days-buttons");
const locationSelect = document.getElementById("location-select");
const howText = document.getElementById("how-text");

/* ---------- DOM / display helpers ---------- */

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function clear(node) {
  node.replaceChildren();
}

// ISO date-times from our API include the location's offset.
// Reading the hours directly avoids silently converting them
// into the user's computer timezone.
function clock(iso) {
  return typeof iso === "string" ? iso.slice(11, 16) : "--:--";
}

function longDate(dateText) {
  const date = new Date(`${dateText}T12:00:00Z`);
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  }).format(date);
}

function locationToday(timeZone) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());

  const part = (type) => parts.find((p) => p.type === type)?.value;
  return `${part("year")}-${part("month")}-${part("day")}`;
}

function addDays(dateText, count) {
  const date = new Date(`${dateText}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + count);
  return date.toISOString().slice(0, 10);
}

function scoreText(score) {
  const number = Number(score);
  return Number.isInteger(number) ? String(number) : number.toFixed(1);
}

function isDaylightHour(hour, day) {
  if (typeof hour.has_light === "boolean") {
    return hour.has_light;
  }

  // Fallback for older backend responses without has_light.
  const start = Date.parse(hour.time);
  const end = start + 60 * 60 * 1000;

  return start < Date.parse(day.sunset) &&
         end > Date.parse(day.sunrise);
}

/* ---------- API communication ---------- */

async function fetchJson(url, signal) {
  let response;

  try {
    response = await fetch(url, { signal });
  } catch (error) {
    if (error.name === "AbortError") throw error;

    throw new Error(
      "Could not reach the server. Please check that Flask is running."
    );
  }

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error(
      "The server returned an unexpected response. Please try again."
    );
  }

  if (!response.ok) {
    throw new Error(
      (data && data.error) ||
      `The server responded with HTTP ${response.status}.`
    );
  }

  if (!data || typeof data !== "object") {
    throw new Error("The server returned an invalid JSON response.");
  }

  return data;
}

/* ---------- Activity and duration controls ---------- */

function buildButtons(container, options, selectedId, onPick) {
  clear(container);

  options.forEach(({ id, label }) => {
    const button = el("button", "", label);
    button.type = "button";
    button.setAttribute("aria-pressed", String(id === selectedId));

    button.addEventListener("click", () => {
      if (id === selectedId) return;

      onPick(id);
      selectedId = id;

      container.querySelectorAll("button").forEach((item, index) => {
        item.setAttribute(
          "aria-pressed",
          String(options[index].id === id)
        );
      });
    });

    container.appendChild(button);
  });
}

function buildActivityButtons(activities) {
  buildButtons(activityButtons, activities, state.activity, (id) => {
    state.activity = id;
    loadRecommendation();
  });
}

function buildDayButtons() {
  buildButtons(
    dayButtons,
    [
      { id: 1, label: "1 day" },
      { id: 2, label: "2 days" },
      { id: 3, label: "3 days" },
    ],
    state.days,
    (id) => {
      state.days = id;
      loadRecommendation();
    }
  );
}

/* ---------- Loading and errors ---------- */

function showLoading() {
  answerBox.className = "answer";
  answerBox.setAttribute("aria-busy", "true");
  clear(answerBox);

  const shell = el("div", "loading-shell");
  shell.setAttribute("role", "status");

  const spinner = el("span", "spinner");
  spinner.setAttribute("aria-hidden", "true");

  shell.appendChild(spinner);
  shell.appendChild(
    document.createTextNode(
      ` Checking weather and daylight for ${LOCATIONS[state.location].name}…`
    )
  );

  answerBox.appendChild(shell);
  clear(daysBox);
}

function showError(message, retry) {
  answerBox.className = "answer is-error";
  answerBox.setAttribute("aria-busy", "false");
  clear(answerBox);

  const card = el("div", "answer-message");
  const icon = el("span", "message-icon", "!");
  icon.setAttribute("aria-hidden", "true");
  card.appendChild(icon);

  const body = el("div");
  body.appendChild(el("h3", "", "We couldn't load the forecast."));
  body.appendChild(el("p", "", message));

  const retryButton = el("button", "retry", "Try again");
  retryButton.type = "button";
  retryButton.addEventListener("click", retry);

  body.appendChild(retryButton);
  card.appendChild(body);
  answerBox.appendChild(card);

  clear(daysBox);
}

/* ---------- Recommendation card ---------- */

function renderAnswer(data) {
  answerBox.className = "answer";
  answerBox.setAttribute("aria-busy", "false");
  clear(answerBox);

  const best = data.best_overall;

  if (!best) {
    const card = el("div", "answer-message");
    const icon = el("span", "message-icon", "☾");
    icon.setAttribute("aria-hidden", "true");

    const body = el("div");
    body.appendChild(
      el("h3", "", "No eligible daylight window found.")
    );
    body.appendChild(
      el(
        "p",
        "",
        "Try a longer forecast, a different location, or another activity."
      )
    );

    card.append(icon, body);
    answerBox.appendChild(card);
    return;
  }

  const location = LOCATIONS[state.location].name;
  const card = el("div", "answer-card");
  const main = el("div", "answer-main");
  const side = el("div", "answer-side");

  main.appendChild(
    el("p", "card-overline", "BEST RECOMMENDED WINDOW")
  );
  main.appendChild(
    el("h3", "", `${clock(best.start)} – ${clock(best.end)}`)
  );
  main.appendChild(
    el("p", "answer-date", longDate(best.date))
  );

  const ratingRow = el("div", "rating-row");

  const ratingStyle =
    best.rating === "Poor"
      ? " rating-poor"
      : best.rating === "Fair"
        ? " rating-fair"
        : "";

  ratingRow.appendChild(
    el(
      "span",
      `rating-pill${ratingStyle}`,
      `${best.rating} for ${data.activity_label || state.activity}`
    )
  );

  ratingRow.appendChild(
    el("span", "answer-location", `${location}, Japan`)
  );

  main.appendChild(ratingRow);

  main.appendChild(
    el(
      "p",
      "answer-subtle",
      "The highest-scoring eligible continuous window in this forecast."
    )
  );

  const scoreArea = el("div", "score-area");
  const ring = el("div", "score-ring");

  ring.setAttribute("role", "img");
  ring.setAttribute(
    "aria-label",
    `Suitability score ${scoreText(best.average_score)} out of 100`
  );

  ring.style.setProperty(
    "--ring-percent",
    `${Math.max(0, Math.min(100, best.average_score))}%`
  );

  if (best.rating === "Poor") {
    ring.style.setProperty("--ring-color", "var(--error)");
  } else if (best.rating === "Fair") {
    ring.style.setProperty("--ring-color", "var(--gold)");
  }

  const inner = el("div", "score-inner");
  inner.appendChild(
    el("span", "score-number", scoreText(best.average_score))
  );
  inner.appendChild(
    el("span", "score-denominator", "/ 100")
  );

  ring.appendChild(inner);
  scoreArea.appendChild(ring);

  const caption = el("div", "score-caption");
  caption.appendChild(
    el("strong", "", `${best.rating} conditions`)
  );
  caption.appendChild(
    document.createTextNode(
      " Based on activity-specific weather and lighting factors."
    )
  );

  scoreArea.appendChild(caption);
  side.appendChild(scoreArea);

  side.appendChild(
    el("h4", "why-title", "Why this time?")
  );

  const reasons = el("ul", "reasons");

  (best.reasons || []).forEach((reason) => {
    reasons.appendChild(el("li", "", reason));
  });

  side.appendChild(reasons);
  card.append(main, side);
  answerBox.appendChild(card);
}

/* ---------- Hourly forecast cards ---------- */

function dayHeading(day, timeZone) {
  const today = locationToday(timeZone);

  const prefix =
    day.date === today
      ? "Today · "
      : day.date === addDays(today, 1)
        ? "Tomorrow · "
        : "";

  return `${prefix}${longDate(day.date)}`;
}

function makeSunTime(label, value, kind) {
  const span = el("span");
  const symbol = el(
    "span",
    "",
    kind === "rise" ? "☀" : "◕"
  );

  symbol.setAttribute("aria-hidden", "true");

  span.append(
    symbol,
    document.createTextNode(`${label} ${clock(value)}`)
  );

  return span;
}

function renderDay(day, activity, timeZone) {
  const section = el("article", "day");

  section.setAttribute(
    "aria-label",
    `Forecast for ${longDate(day.date)}`
  );

  const header = el("div", "day-heading");
  const headerLeft = el("div");

  headerLeft.appendChild(
    el("h3", "day-title", dayHeading(day, timeZone))
  );

  headerLeft.appendChild(
    el("p", "day-date-context", "Hourly activity suitability")
  );

  header.appendChild(headerLeft);

  const sun = el("div", "sun-times");
  sun.appendChild(
    makeSunTime("Sunrise", day.sunrise, "rise")
  );
  sun.appendChild(
    makeSunTime("Sunset", day.sunset, "set")
  );

  header.appendChild(sun);
  section.appendChild(header);

  const best = day.best_window;

  if (best) {
    const windowLine = el("div", "window-line");
    const swatch = el("span", "window-swatch");
    swatch.setAttribute("aria-hidden", "true");

    windowLine.appendChild(swatch);

    const message = el("span");

    message.appendChild(
      el(
        "strong",
        "",
        `${clock(best.start)}–${clock(best.end)}`
      )
    );

    message.appendChild(
      document.createTextNode(
        ` · ${best.rating} · ${scoreText(best.average_score)}/100 average`
      )
    );

    windowLine.appendChild(message);
    section.appendChild(windowLine);
  } else {
    section.appendChild(
      el(
        "p",
        "day-note",
        day.note || "No eligible daytime window remains for this date."
      )
    );
  }

  if (!Array.isArray(day.hours) || day.hours.length === 0) {
    section.appendChild(
      el(
        "p",
        "day-note",
        "No hourly forecast data is available for this date."
      )
    );
    return section;
  }

  const strip = el("div", "strip");
  strip.setAttribute("role", "group");

  strip.setAttribute(
    "aria-label",
    `Hourly scores for ${longDate(day.date)}`
  );

  const detail = el("div", "detail");
  const columns = [];

  const bestStart = best ? Date.parse(best.start) : NaN;
  const bestEnd = best ? Date.parse(best.end) : NaN;

  function select(hour, column, hasLight) {
    columns.forEach((other) => {
      other.setAttribute("aria-pressed", "false");
    });

    column.setAttribute("aria-pressed", "true");
    renderDetail(detail, hour, activity, hasLight);
  }

  day.hours.forEach((hour) => {
    const time = Date.parse(hour.time);
    const hasLight = isDaylightHour(hour, day);

    const inBest =
      Boolean(best) &&
      hasLight &&
      time >= bestStart &&
      time < bestEnd;

    const column = el(
      "button",
      `col${inBest ? " in-best" : ""}${hasLight ? "" : " is-night"}`
    );

    column.type = "button";
    column.setAttribute("aria-pressed", "false");

    column.setAttribute(
      "aria-label",
      `${clock(hour.time)}, suitability score ${scoreText(hour.score)} out of 100` +
      `${hasLight ? "" : ", night, not eligible for recommendation"}`
    );

    const area = el("div", "col-area");

    area.appendChild(
      el("div", "col-value", String(Math.round(hour.score)))
    );

    const bar = el("div", "bar");

    bar.style.setProperty(
      "--score",
      String(Math.max(0, Math.min(1, hour.score / 100)))
    );

    area.appendChild(bar);
    column.appendChild(area);

    column.appendChild(
      el("div", "col-label", clock(hour.time).slice(0, 2))
    );

    column.addEventListener(
      "click",
      () => select(hour, column, hasLight)
    );

    strip.appendChild(column);
    columns.push(column);
  });

  section.appendChild(strip);

  section.appendChild(
    el(
      "p",
      "strip-help",
      "Select an hour to see all four scoring factors. " +
      "Grey bars represent nighttime hours that cannot be recommended."
    )
  );

  section.appendChild(detail);

  // Prefer the earliest hour in the best window.
  // Otherwise, select the first daylight hour.
  let initialIndex = best
    ? day.hours.findIndex(
        (hour) =>
          Date.parse(hour.time) >= bestStart &&
          isDaylightHour(hour, day)
      )
    : -1;

  if (initialIndex < 0) {
    initialIndex = day.hours.findIndex(
      (hour) => isDaylightHour(hour, day)
    );
  }

  if (initialIndex < 0) {
    initialIndex = 0;
  }

  select(
    day.hours[initialIndex],
    columns[initialIndex],
    isDaylightHour(day.hours[initialIndex], day)
  );

  return section;
}

/* ---------- Individual hourly score details ---------- */

function renderDetail(container, hour, activity, hasLight) {
  clear(container);

  const start = clock(hour.time);

  const endHour = String(
    (Number(start.slice(0, 2)) + 1) % 24
  ).padStart(2, "0");

  const header = el("div", "detail-top");

  header.appendChild(
    el(
      "h4",
      "",
      `${start}–${endHour}:00 · ${scoreText(hour.score)}/100`
    )
  );

  header.appendChild(
    el(
      "span",
      `detail-badge${hasLight ? "" : " is-night"}`,
      hasLight ? "Eligible lighting" : "Night · not eligible"
    )
  );

  container.appendChild(header);

  const labels = {
    temperature: `Temperature · ${hour.temperature.toFixed(1)} °C`,
    rain: `Rain chance · ${hour.rain_probability}%`,
    wind: `Wind · ${hour.wind_speed.toFixed(1)} km/h`,
    lighting:
      activity === "photography"
        ? `Lighting · ${hour.cloud_cover}% cloud`
        : "Daylight / lighting",
  };

  FACTORS.forEach(({ key }) => {
    const points = Number(hour.breakdown[key] || 0);
    const max = Number(state.maxPoints[key] || 1);

    const row = el("div", "factor");

    row.appendChild(
      el("span", "factor-label", labels[key])
    );

    const meter = el("div", "meter");
    meter.setAttribute("role", "meter");
    meter.setAttribute("aria-label", `${key} score`);
    meter.setAttribute("aria-valuemin", "0");
    meter.setAttribute("aria-valuemax", String(max));
    meter.setAttribute("aria-valuenow", String(points));

    const fill = el("span");

    fill.style.setProperty(
      "--fill",
      `${Math.max(0, Math.min(100, (points / max) * 100))}%`
    );

    meter.appendChild(fill);
    row.appendChild(meter);

    row.appendChild(
      el("span", "points", `${scoreText(points)} / ${max}`)
    );

    container.appendChild(row);
  });

  container.appendChild(
    el(
      "p",
      "detail-note",
      hasLight
        ? "Scores are heuristic suitability estimates, not weather or safety guarantees."
        : "This is a weather-only score. This hour is excluded from recommended outdoor windows because of insufficient light."
    )
  );
}

/* ---------- Render forecast days ---------- */

function renderDays(data) {
  clear(daysBox);

  const timeZone = data.location?.timezone || "Asia/Tokyo";

  (data.days || []).forEach((day) => {
    daysBox.appendChild(
      renderDay(day, data.activity, timeZone)
    );
  });
}

/* ---------- Connect to Flask ---------- */

async function loadRecommendation() {
  const requestId = ++state.requestId;

  if (state.abortController) {
    state.abortController.abort();
  }

  const controller = new AbortController();
  state.abortController = controller;

  showLoading();

  const location = LOCATIONS[state.location];

  const params = new URLSearchParams({
    activity: state.activity,
    days: String(state.days),
  });

  // Kyoto is already the default location in Flask config.
  if (state.location !== "kyoto") {
    params.set("lat", String(location.latitude));
    params.set("lng", String(location.longitude));
  }

  try {
    const data = await fetchJson(
      `/api/recommendation?${params.toString()}`,
      controller.signal
    );

    // Ignore responses from older requests.
    if (requestId !== state.requestId) return;

    if (!Array.isArray(data.days)) {
      throw new Error("The forecast format was incomplete.");
    }

    renderAnswer(data);
    renderDays(data);

  } catch (error) {
    if (
      requestId !== state.requestId ||
      error.name === "AbortError"
    ) {
      return;
    }

    showError(error.message, loadRecommendation);

  } finally {
    if (requestId === state.requestId) {
      state.abortController = null;
    }
  }
}

/* ---------- Explain the scoring algorithm ---------- */

function renderHowItWorks() {
  clear(howText);

  const max = state.maxPoints;

  howText.appendChild(
    el(
      "p",
      "",
      `Every hour receives up to 100 points: ` +
      `temperature (${max.temperature}), ` +
      `rain (${max.rain}), ` +
      `wind (${max.wind}), and ` +
      `lighting (${max.lighting}).`
    )
  );

  howText.appendChild(
    el(
      "p",
      "",
      "Walking, cycling and photography use different rules. " +
      "The service combines weather with sunrise, sunset and " +
      "photography lighting periods, then considers consecutive " +
      "three-hour windows with eligible light."
    )
  );
}

/* ---------- Initialize the application ---------- */

function revealHowHeading() {
  const heading = document.getElementById("how-title");

  if (!heading || !("IntersectionObserver" in window) ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      heading.classList.add("is-revealing");
      observer.disconnect();
    }
  }, { threshold: 0.3 });

  observer.observe(heading);
}

async function init() {
  revealHowHeading();
  buildDayButtons();

  locationSelect.addEventListener("change", () => {
    if (!Object.hasOwn(LOCATIONS, locationSelect.value)) {
      return;
    }

    state.location = locationSelect.value;
    loadRecommendation();
  });

  try {
    const data = await fetchJson("/api/activities");

    if (
      !Array.isArray(data.activities) ||
      !data.max_points
    ) {
      throw new Error(
        "Activity settings are missing from the API response."
      );
    }

    state.maxPoints = data.max_points;
    buildActivityButtons(data.activities);
    renderHowItWorks();

    loadRecommendation();

  } catch (error) {
    showError(
      error.message,
      () => window.location.reload()
    );
  }
}

init();
