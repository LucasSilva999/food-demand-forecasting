
const API_BASE = "http://127.0.0.1:8000";

const $ = (selector) => document.querySelector(selector);

const form = $("#prediction-form");
const predictButton = $("#predict-button");
const resultPanel = $("#prediction-result");
const errorMessage = $("#prediction-error");

const apiStatusDot = $("#api-status-dot");
const apiStatusText = $("#api-status-text");

const chartContainer = $("#demand-chart");
const chartSummary = $("#chart-summary");

const hourInput = $("#hour");
const weekdayInput = $("#weekday");
const promotionInput = $("#promotion");
const weatherInput = $("#weather");
const zoneInput = $("#zone");

let apiAvailable = false;
let chartRequestId = 0;
let chartTimer = null;
let apiCheckInProgress = false;

const formatNumber = (value, digits = 1) =>
    Number(value).toLocaleString("en-US", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
    });

const escapeHTML = (value) =>
    String(value).replace(/[&<>"']/g, (character) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);

/* ========================================
   API STATUS
======================================== */

function setAPIStatus(connected) {
    apiAvailable = connected;

    apiStatusDot.className = connected
        ? "status-dot online"
        : "status-dot offline";

    apiStatusText.textContent = connected
        ? "API Connected"
        : "API Offline";

    document.body.classList.toggle("api-online", connected);
}

async function checkAPI() {
    if (apiCheckInProgress) return apiAvailable;

    apiCheckInProgress = true;

    try {
        const response = await fetch(`${API_BASE}/health`, {
            signal: AbortSignal.timeout(5000)
        });

        if (!response.ok) {
            throw new Error("API unavailable");
        }

        const data = await response.json();

        if (!data.model_loaded) {
            throw new Error("Model not loaded");
        }

        setAPIStatus(true);
        return true;

    } catch (error) {
        setAPIStatus(false);
        console.error("API connection error:", error);
        return false;

    } finally {
        apiCheckInProgress = false;
    }
}

/* ========================================
   DATE
======================================== */

function updateDate() {
    const dateElement = $("#current-date");

    if (!dateElement) return;

    dateElement.textContent = new Date().toLocaleDateString(
        "en-US",
        {
            month: "short",
            day: "numeric",
            year: "numeric"
        }
    );
}

/* ========================================
   METRIC ANIMATIONS
======================================== */

function animateMetricValues() {
    const metrics = document.querySelectorAll(".metric-value");

    metrics.forEach((element) => {
        const original = element.textContent.trim();
        const target = Number(original.replace("%", ""));

        if (!Number.isFinite(target)) return;

        const suffix = original.includes("%") ? "%" : "";
        const decimals = original.includes(".")
            ? original.split(".")[1].replace("%", "").length
            : 0;

        const duration = 1100;
        const startTime = performance.now();

        function frame(currentTime) {
            const progress = Math.min(
                (currentTime - startTime) / duration,
                1
            );

            const eased = 1 - Math.pow(1 - progress, 4);
            const current = target * eased;

            element.textContent =
                current.toFixed(decimals) + suffix;

            if (progress < 1) {
                requestAnimationFrame(frame);
            }
        }

        element.textContent = (0).toFixed(decimals) + suffix;
        requestAnimationFrame(frame);
    });
}

/* ========================================
   FORM DATA
======================================== */

function getFormData() {
    return {
        hour: Number(hourInput.value),
        weekday: Number(weekdayInput.value),
        promotion: Number(promotionInput.value),
        weather: weatherInput.value,
        zone: zoneInput.value
    };
}

function getChartScenario() {
    const data = getFormData();

    return {
        weekday: data.weekday,
        promotion: data.promotion,
        weather: data.weather,
        zone: data.zone
    };
}

/* ========================================
   API PREDICTION
======================================== */

async function requestPrediction(inputData) {
    const response = await fetch(`${API_BASE}/predict`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(inputData),
        signal: AbortSignal.timeout(15000)
    });

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error("Invalid response from prediction API.");
    }

    if (!response.ok) {
        const detail = data.detail || "Prediction request failed";

        throw new Error(
            typeof detail === "string"
                ? detail
                : JSON.stringify(detail)
        );
    }

    if (!Number.isFinite(Number(data.predicted_orders))) {
        throw new Error("The API returned an invalid prediction.");
    }

    return data;
}

/* ========================================
   BUTTON STATE
======================================== */

function setButtonLoading(loading) {
    if (!predictButton) return;

    predictButton.disabled = loading;

    predictButton.innerHTML = loading
        ? `
            <span class="button-label">
                <span class="loading-spinner"></span>
                Generating prediction...
            </span>
            <span class="button-arrow">...</span>
        `
        : `
            <span class="button-label">Generate prediction</span>
            <span class="button-arrow" aria-hidden="true">→</span>
        `;
}

/* ========================================
   PREDICTION RESULT
======================================== */

function animatePredictionValue(element, target) {
    const duration = 850;
    const startTime = performance.now();

    function frame(currentTime) {
        const progress = Math.min(
            (currentTime - startTime) / duration,
            1
        );

        const eased = 1 - Math.pow(1 - progress, 3);
        const value = target * eased;

        element.textContent = formatNumber(value, 2);

        if (progress < 1) {
            requestAnimationFrame(frame);
        }
    }

    requestAnimationFrame(frame);
}

form?.addEventListener("submit", async (event) => {
    event.preventDefault();

    resultPanel.classList.add("hidden");
    errorMessage.classList.add("hidden");

    if (!apiAvailable && !(await checkAPI())) {
        errorMessage.textContent =
            "The API is offline. Please check the connection.";

        errorMessage.classList.remove("hidden");
        return;
    }

    const inputData = getFormData();

    setButtonLoading(true);

    try {
        const result = await requestPrediction(inputData);

        const output = $("#predicted-orders");

        animatePredictionValue(
            output,
            Number(result.predicted_orders)
        );

        const context = $("#prediction-context");

        if (context) {
            context.textContent =
                `${String(inputData.hour).padStart(2, "0")}:00 · ` +
                `${inputData.zone} zone · ` +
                `${inputData.promotion ? "Promotion active" : "No promotion"}`;
        }

        resultPanel.classList.remove("hidden");
        resultPanel.classList.remove("result-enter");
        void resultPanel.offsetWidth;
        resultPanel.classList.add("result-enter");

    } catch (error) {
        if (error.name === "AbortError" || error.name === "TimeoutError") {
            errorMessage.textContent = "The prediction request timed out.";
        } else {
            errorMessage.textContent = error.message;
        }

        errorMessage.classList.remove("hidden");

    } finally {
        setButtonLoading(false);
    }
});

/* ========================================
   CHART LOADING
======================================== */

function showChartLoading(message) {
    chartContainer.innerHTML = `
        <div class="chart-loading">
            <span class="loading-spinner"></span>
            <span>${escapeHTML(message)}</span>
        </div>
    `;
}

function scheduleChartUpdate() {
    clearTimeout(chartTimer);

    chartTimer = setTimeout(() => {
        loadHourlyForecast();
    }, 350);
}

async function loadHourlyForecast() {
    const requestId = ++chartRequestId;

    if (!apiAvailable && !(await checkAPI())) {
        if (requestId !== chartRequestId) return;

        chartContainer.innerHTML = `
            <div class="chart-loading">
                API unavailable. Waiting for connection...
            </div>
        `;

        chartSummary.textContent = "API unavailable";
        return;
    }

    showChartLoading("Calculating hourly demand...");

    const scenario = getChartScenario();

    try {
        const requests = Array.from(
            { length: 24 },
            (_, hour) => requestPrediction({
                ...scenario,
                hour
            })
        );

        const results = await Promise.all(requests);

        if (requestId !== chartRequestId) return;

        const predictions = results.map(
            (result) => Number(result.predicted_orders)
        );

        renderChart(predictions);

        const peak = Math.max(...predictions);
        const lowest = Math.min(...predictions);

        const peakHour = predictions.indexOf(peak);
        const lowestHour = predictions.indexOf(lowest);

        chartSummary.textContent =
            `Peak ${formatNumber(peak)} orders at ${String(peakHour).padStart(2, "0")}:00`;

        const scenarioLabel =
            `${scenario.zone} · ${scenario.weather} · ` +
            `${scenario.promotion ? "Promotion" : "No promotion"}`;

        chartContainer.setAttribute("data-scenario", scenarioLabel);

        const chartDescription = $("#chart-scenario");

        if (chartDescription) {
            chartDescription.textContent = scenarioLabel;
        }

        console.info("Hourly forecast loaded", {
            peak,
            peakHour,
            lowest,
            lowestHour
        });

    } catch (error) {
        if (requestId !== chartRequestId) return;

        chartContainer.innerHTML = `
            <div class="chart-loading">
                Unable to load forecast data. Please try again.
            </div>
        `;

        chartSummary.textContent = "Forecast unavailable";

        console.error("Hourly forecast error:", error);
    }
}

/* ========================================
   SMOOTH SVG PATH
======================================== */

function createSmoothPath(points) {
    if (!points.length) return "";

    if (points.length === 1) {
        return `M ${points[0].x} ${points[0].y}`;
    }

    let path = `M ${points[0].x} ${points[0].y}`;

    for (let index = 0; index < points.length - 1; index++) {
        const current = points[index];
        const next = points[index + 1];

        const middleX = (current.x + next.x) / 2;

        path +=
            ` C ${middleX} ${current.y}, ` +
            `${middleX} ${next.y}, ` +
            `${next.x} ${next.y}`;
    }

    return path;
}

/* ========================================
   INTERACTIVE CHART
======================================== */

function renderChart(values) {
    const width = 1000;
    const height = 320;

    const margin = {
        top: 30,
        right: 35,
        bottom: 42,
        left: 58
    };

    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    const maximum = Math.max(...values, 1);
    const minimum = Math.min(...values, 0);

    const maxValue = Math.ceil(maximum * 1.18 / 10) * 10;
    const minValue = Math.max(0, Math.floor(minimum * 0.85 / 10) * 10);

    const valueRange = Math.max(maxValue - minValue, 1);

    const x = (index) =>
        margin.left + (index / 23) * chartWidth;

    const y = (value) =>
        margin.top + chartHeight -
        ((value - minValue) / valueRange) * chartHeight;

    const points = values.map((value, index) => ({
        x: x(index),
        y: y(value),
        value,
        hour: index
    }));

    const linePath = createSmoothPath(points);
    const bottom = margin.top + chartHeight;

    const areaPath =
        `${linePath} L ${points[23].x} ${bottom} ` +
        `L ${points[0].x} ${bottom} Z`;

    const peakValue = Math.max(...values);
    const lowValue = Math.min(...values);

    const peakIndex = values.indexOf(peakValue);
    const lowIndex = values.indexOf(lowValue);

    const peakPoint = points[peakIndex];
    const lowPoint = points[lowIndex];

    const gradientId = `area-gradient-${Date.now()}`;
    const gridId = `chart-grid-${Date.now()}`;

    const gridLines = Array.from({ length: 5 }, (_, index) => {
        const value = minValue + valueRange * index / 4;
        const position = y(value);

        return `
            <line
                x1="${margin.left}"
                y1="${position}"
                x2="${width - margin.right}"
                y2="${position}"
                stroke="#71809a"
                stroke-opacity="0.15"
                stroke-dasharray="4 7"
            />

            <text
                x="${margin.left - 13}"
                y="${position + 4}"
                fill="#8492a8"
                font-size="11"
                text-anchor="end"
            >${value.toFixed(0)}</text>
        `;
    }).join("");

    const hourLabels = Array.from({ length: 24 }, (_, hour) => {
        if (hour % 2 !== 0) return "";

        return `
            <text
                x="${x(hour)}"
                y="${height - 12}"
                fill="#8492a8"
                font-size="10"
                text-anchor="middle"
            >${String(hour).padStart(2, "0")}:00</text>
        `;
    }).join("");

    chartContainer.innerHTML = `
        <div class="chart-tooltip" id="chart-tooltip" role="status">
            <span class="tooltip-hour"></span>
            <strong class="tooltip-value"></strong>
            <span class="tooltip-caption">Predicted orders</span>
        </div>

        <svg
            id="forecast-svg"
            viewBox="0 0 ${width} ${height}"
            role="img"
            aria-label="Hourly demand forecast with 24 predicted values"
            preserveAspectRatio="xMidYMid meet"
        >
            <defs>
                <linearGradient
                    id="${gradientId}"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                >
                    <stop offset="0%" stop-color="#579cff" stop-opacity="0.34"/>
                    <stop offset="100%" stop-color="#579cff" stop-opacity="0.015"/>
                </linearGradient>

                <clipPath id="${gridId}">
                    <rect
                        x="${margin.left}"
                        y="${margin.top}"
                        width="${chartWidth}"
                        height="${chartHeight}"
                    />
                </clipPath>
            </defs>

            ${gridLines}

            <g clip-path="url(#${gridId})">
                <path
                    class="chart-area"
                    d="${areaPath}"
                    fill="url(#${gradientId})"
                />

                <path
                    class="chart-line"
                    d="${linePath}"
                    fill="none"
                    stroke="#65a7ff"
                    stroke-width="3.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                />

                <line
                    id="chart-crosshair"
                    x1="${peakPoint.x}"
                    y1="${margin.top}"
                    x2="${peakPoint.x}"
                    y2="${bottom}"
                    stroke="#9bbfff"
                    stroke-opacity="0.5"
                    stroke-dasharray="4 5"
                    visibility="hidden"
                />

                <circle
                    cx="${peakPoint.x}"
                    cy="${peakPoint.y}"
                    r="5"
                    fill="#34d399"
                    stroke="#10201f"
                    stroke-width="3"
                />

                <circle
                    cx="${lowPoint.x}"
                    cy="${lowPoint.y}"
                    r="5"
                    fill="#fbbf72"
                    stroke="#292016"
                    stroke-width="3"
                />

                ${points.map((point, index) => `
                    <circle
                        class="chart-point"
                        data-hour="${index}"
                        cx="${point.x}"
                        cy="${point.y}"
                        r="11"
                        fill="transparent"
                        tabindex="0"
                        role="button"
                        aria-label="${String(index).padStart(2, "0")}:00, ${formatNumber(point.value, 2)} predicted orders"
                    />
                `).join("")}
            </g>

            <text
                x="${peakPoint.x}"
                y="${Math.max(peakPoint.y - 16, 15)}"
                fill="#34d399"
                font-size="10"
                font-weight="700"
                text-anchor="middle"
            >PEAK</text>

            <text
                x="${lowPoint.x}"
                y="${Math.min(lowPoint.y + 23, bottom - 5)}"
                fill="#fbbf72"
                font-size="10"
                font-weight="700"
                text-anchor="middle"
            >LOW</text>

            ${hourLabels}
        </svg>
    `;

    setupChartTooltip(points, width, height);

    chartSummary.textContent =
        `Peak: ${formatNumber(peakValue)} orders · ` +
        `${String(peakIndex).padStart(2, "0")}:00`;
}

/* ========================================
   TOOLTIP INTERACTION
======================================== */

function setupChartTooltip(points, width, height) {
    const svg = $("#forecast-svg");
    const tooltip = $("#chart-tooltip");
    const crosshair = $("#chart-crosshair");

    if (!svg || !tooltip) return;

    const showTooltip = (index) => {
        const point = points[index];

        if (!point) return;

        const rect = svg.getBoundingClientRect();

        const left = (point.x / width) * rect.width;
        const top = (point.y / height) * rect.height;

        tooltip.querySelector(".tooltip-hour").textContent =
            `${String(index).padStart(2, "0")}:00`;

        tooltip.querySelector(".tooltip-value").textContent =
            `${formatNumber(point.value, 2)} orders`;

        tooltip.classList.add("visible");

        const tooltipWidth = tooltip.offsetWidth || 150;

        tooltip.style.left = `${Math.max(
            5,
            Math.min(left, rect.width - tooltipWidth - 5)
        )}px`;

        tooltip.style.top = `${Math.max(0, top - 75)}px`;

        if (crosshair) {
            crosshair.setAttribute("x1", point.x);
            crosshair.setAttribute("x2", point.x);
            crosshair.setAttribute("visibility", "visible");
        }
    };

    const hideTooltip = () => {
        tooltip.classList.remove("visible");

        if (crosshair) {
            crosshair.setAttribute("visibility", "hidden");
        }
    };

    const getIndexFromPointer = (event) => {
        const rect = svg.getBoundingClientRect();

        const relativeX =
            (event.clientX - rect.left) / rect.width;

        return Math.max(
            0,
            Math.min(
                23,
                Math.round(relativeX * 23)
            )
        );
    };

    svg.addEventListener("pointermove", (event) => {
        showTooltip(getIndexFromPointer(event));
    });

    svg.addEventListener("pointerleave", hideTooltip);

    svg.querySelectorAll(".chart-point").forEach((point) => {
        const index = Number(point.dataset.hour);

        point.addEventListener("focus", () => showTooltip(index));
        point.addEventListener("blur", hideTooltip);
        point.addEventListener("click", () => showTooltip(index));
    });
}

/* ========================================
   SCENARIO FILTERS
======================================== */

[
    weekdayInput,
    promotionInput,
    weatherInput,
    zoneInput
].forEach((input) => {
    input?.addEventListener("change", scheduleChartUpdate);
});

/* ========================================
   API RECOVERY
======================================== */

async function monitorAPI() {
    const wasAvailable = apiAvailable;
    const connected = await checkAPI();

    if (connected && !wasAvailable) {
        loadHourlyForecast();
    }
}

/* ========================================
   INITIALIZATION
======================================== */

async function initializeDashboard() {
    updateDate();

    animateMetricValues();

    const connected = await checkAPI();

    if (connected) {
        await loadHourlyForecast();
    } else {
        chartContainer.innerHTML = `
            <div class="chart-loading">
                Start the API to load the hourly forecast.
            </div>
        `;

        chartSummary.textContent = "API unavailable";
    }

    // Check API connection every 15 seconds.
    window.setInterval(monitorAPI, 15000);
}

initializeDashboard();


/* ========================================
   NAVIGATION ACTIVE STATE
======================================== */

document.querySelectorAll(".navigation a").forEach((link) => {
    link.addEventListener("click", () => {
        document.querySelectorAll(".navigation a").forEach((item) => {
            item.classList.remove("active");
        });

        link.classList.add("active");
    });
});
