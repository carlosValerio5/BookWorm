const CHART_WIDTH = 640;
const CHART_HEIGHT = 220;
const CHART_PADDING = 10;
const POLL_INTERVAL_MILLISECONDS = 2000;

const LOSS_SERIES = [
  { key: "train", label: "train loss", color: "#9fbbe0" },
  { key: "val", label: "val loss", color: "#f54e00" },
];

const ACCURACY_SERIES = [
  { key: "precision(B)", label: "precision", color: "#9fc9a2" },
  { key: "recall(B)", label: "recall", color: "#e6c07b" },
  { key: "mAP50(B)", label: "mAP50", color: "#9fbbe0" },
  { key: "mAP50-95(B)", label: "mAP50-95", color: "#c0a8dd" },
];

const runNameElement = document.getElementById("run-name");
const epochStatusElement = document.getElementById("epoch-status");
const emptyStageElement = document.getElementById("empty-stage");
const chartsElement = document.getElementById("charts");
const lossChartElement = document.getElementById("loss-chart");
const accuracyChartElement = document.getElementById("accuracy-chart");
const lossLegendElement = document.getElementById("loss-legend");
const accuracyLegendElement = document.getElementById("accuracy-legend");
const statusEpochElement = document.getElementById("status-epoch");
const statusPollElement = document.getElementById("status-poll");

function sumValues(valuesByKey) {
  return Object.values(valuesByKey).reduce((total, value) => total + value, 0);
}

function toChartPoints(values, minValue, maxValue) {
  const valueRange = maxValue - minValue || 1;
  return values.map((value, index) => {
    const x = CHART_PADDING + (index / Math.max(values.length - 1, 1)) * (CHART_WIDTH - CHART_PADDING * 2);
    const y = CHART_HEIGHT - CHART_PADDING - ((value - minValue) / valueRange) * (CHART_HEIGHT - CHART_PADDING * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
}

function buildGridLine(y) {
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("class", "chart-grid-line");
  line.setAttribute("x1", String(CHART_PADDING));
  line.setAttribute("x2", String(CHART_WIDTH - CHART_PADDING));
  line.setAttribute("y1", String(y));
  line.setAttribute("y2", String(y));
  return line;
}

function buildChartLine(points, color) {
  const polyline = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  polyline.setAttribute("class", "chart-line");
  polyline.setAttribute("points", points.join(" "));
  polyline.setAttribute("stroke", color);
  return polyline;
}

function buildLegendItem({ label, color }) {
  const item = document.createElement("li");
  item.className = "legend-item";
  const swatch = document.createElement("span");
  swatch.className = "legend-swatch";
  swatch.style.background = color;
  const text = document.createElement("span");
  text.textContent = label;
  item.append(swatch, text);
  return item;
}

function drawSeriesOnChart(chartElement, seriesValues, minValue, maxValue) {
  chartElement.replaceChildren();
  [0, 0.5, 1].forEach((fraction) => chartElement.append(buildGridLine(CHART_PADDING + fraction * (CHART_HEIGHT - CHART_PADDING * 2))));
  seriesValues.forEach(({ values, color }) => {
    chartElement.append(buildChartLine(toChartPoints(values, minValue, maxValue), color));
  });
}

function renderLossChart(epochs) {
  const trainTotals = epochs.map((epoch) => sumValues(epoch.train_losses));
  const valTotals = epochs.map((epoch) => sumValues(epoch.val_losses));
  drawSeriesOnChart(
    lossChartElement,
    [
      { values: trainTotals, color: LOSS_SERIES[0].color },
      { values: valTotals, color: LOSS_SERIES[1].color },
    ],
    0,
    Math.max(...trainTotals, ...valTotals, 0.01),
  );
  lossLegendElement.replaceChildren(...LOSS_SERIES.map(buildLegendItem));
}

function renderAccuracyChart(epochs) {
  drawSeriesOnChart(
    accuracyChartElement,
    ACCURACY_SERIES.map(({ key, color }) => ({ color, values: epochs.map((epoch) => epoch.val_metrics[key] ?? 0) })),
    0,
    1,
  );
  accuracyLegendElement.replaceChildren(...ACCURACY_SERIES.map(buildLegendItem));
}

function renderStage(epochs) {
  const hasEpochs = epochs.length > 0;
  emptyStageElement.hidden = hasEpochs;
  chartsElement.hidden = !hasEpochs;
  if (!hasEpochs) {
    epochStatusElement.textContent = "";
    statusEpochElement.textContent = "";
    return;
  }
  const lastEpoch = epochs[epochs.length - 1];
  epochStatusElement.textContent = `Epoch ${lastEpoch.epoch}`;
  statusEpochElement.textContent = `${epochs.length} epoch${epochs.length === 1 ? "" : "s"} logged`;
}

function renderMetrics(epochs) {
  renderStage(epochs);
  if (epochs.length > 0) {
    renderLossChart(epochs);
    renderAccuracyChart(epochs);
  }
}

async function fetchMetrics() {
  const response = await fetch("/api/metrics");
  return response.ok ? response.json() : [];
}

async function pollMetrics() {
  const epochs = await fetchMetrics();
  renderMetrics(epochs);
  statusPollElement.textContent = `updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
}

function pollMetricsAndReportFailure() {
  pollMetrics().catch(() => {
    statusPollElement.textContent = "Could not reach the dashboard server";
  });
}

window.setInterval(pollMetricsAndReportFailure, POLL_INTERVAL_MILLISECONDS);
pollMetricsAndReportFailure();
