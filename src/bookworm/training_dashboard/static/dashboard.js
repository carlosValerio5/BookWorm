const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const CHART_WIDTH = 640;
const CHART_HEIGHT = 220;
const PAD_LEFT = 42;
const PAD_RIGHT = 10;
const PAD_TOP = 10;
const PAD_BOTTOM = 22;
const PLOT_WIDTH = CHART_WIDTH - PAD_LEFT - PAD_RIGHT;
const PLOT_HEIGHT = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;
const Y_AXIS_TICK_FRACTIONS = [0, 0.5, 1];
const MAX_X_AXIS_TICKS = 6;
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

const PARAM_LABELS = {
  model: "Base weights",
  data: "Dataset",
  epochs: "Epochs",
  batch: "Batch size",
  imgsz: "Image size",
  optimizer: "Optimizer",
  lr0: "Learning rate",
};
const PARAM_ORDER = ["model", "data", "epochs", "batch", "imgsz", "optimizer", "lr0"];

const appWindowElement = document.getElementById("app-window");
const backButtonElement = document.getElementById("back-button");
const runNameElement = document.getElementById("run-name");
const epochStatusElement = document.getElementById("epoch-status");
const viewListElement = document.getElementById("view-list");
const viewRunElement = document.getElementById("view-run");
const runsEmptyElement = document.getElementById("runs-empty");
const runsListElement = document.getElementById("runs-list");
const emptyStageElement = document.getElementById("empty-stage");
const chartsElement = document.getElementById("charts");
const lossLegendElement = document.getElementById("loss-legend");
const accuracyLegendElement = document.getElementById("accuracy-legend");
const statusEpochElement = document.getElementById("status-epoch");
const statusPollElement = document.getElementById("status-poll");
const runPaneElement = document.getElementById("run-pane");
const runParamsElement = document.getElementById("run-params");
const runParamsEmptyElement = document.getElementById("run-params-empty");

let currentRoute = { view: "list" };
let latestEpochs = [];
let latestRunInfo = { run_name: null, params: {}, baseline: null };

function clamp(value, minValue, maxValue) {
  return Math.min(Math.max(value, minValue), maxValue);
}

function sumValues(valuesByKey) {
  return Object.values(valuesByKey).reduce((total, value) => total + value, 0);
}

function formatValue(value) {
  if (value === 0) {
    return "0";
  }
  return Math.abs(value) >= 10 ? value.toFixed(1) : value.toFixed(3);
}

function xForIndex(index, epochCount) {
  return PAD_LEFT + (epochCount <= 1 ? 0 : (index / (epochCount - 1)) * PLOT_WIDTH);
}

function yForValue(value, minValue, maxValue) {
  const range = maxValue - minValue || 1;
  return PAD_TOP + PLOT_HEIGHT - ((value - minValue) / range) * PLOT_HEIGHT;
}

function pickXAxisTicks(epochCount) {
  if (epochCount <= MAX_X_AXIS_TICKS) {
    return Array.from({ length: epochCount }, (_, index) => index);
  }
  const lastIndex = epochCount - 1;
  const tickIndexes = new Set();
  for (let step = 0; step < MAX_X_AXIS_TICKS; step += 1) {
    tickIndexes.add(Math.round((step / (MAX_X_AXIS_TICKS - 1)) * lastIndex));
  }
  return [...tickIndexes].sort((a, b) => a - b);
}

function svgElement(tagName) {
  return document.createElementNS(SVG_NAMESPACE, tagName);
}

function buildGridLine(y) {
  const line = svgElement("line");
  line.setAttribute("class", "chart-grid-line");
  line.setAttribute("x1", String(PAD_LEFT));
  line.setAttribute("x2", String(CHART_WIDTH - PAD_RIGHT));
  line.setAttribute("y1", String(y));
  line.setAttribute("y2", String(y));
  return line;
}

function buildAxisLabel(x, y, text, anchor) {
  const label = svgElement("text");
  label.setAttribute("class", "chart-axis-label");
  label.setAttribute("x", String(x));
  label.setAttribute("y", String(y));
  label.setAttribute("text-anchor", anchor);
  label.textContent = text;
  return label;
}

function buildAxisElements(epochs, minValue, maxValue) {
  const elements = [];
  Y_AXIS_TICK_FRACTIONS.forEach((fraction) => {
    const value = minValue + fraction * (maxValue - minValue);
    const y = yForValue(value, minValue, maxValue);
    elements.push(buildGridLine(y));
    elements.push(buildAxisLabel(PAD_LEFT - 7, y + 3.5, formatValue(value), "end"));
  });
  pickXAxisTicks(epochs.length).forEach((index) => {
    elements.push(buildAxisLabel(xForIndex(index, epochs.length), CHART_HEIGHT - PAD_BOTTOM + 16, String(epochs[index].epoch), "middle"));
  });
  return elements;
}

function pointsAttribute(values, epochCount, minValue, maxValue) {
  return values.map((value, index) => `${xForIndex(index, epochCount).toFixed(1)},${yForValue(value, minValue, maxValue).toFixed(1)}`).join(" ");
}

function buildLine(points, color) {
  const polyline = svgElement("polyline");
  polyline.setAttribute("class", "chart-line");
  polyline.setAttribute("points", points);
  polyline.setAttribute("stroke", color);
  return polyline;
}

function buildDot(x, y, color) {
  const circle = svgElement("circle");
  circle.setAttribute("class", "chart-dot");
  circle.setAttribute("cx", String(x));
  circle.setAttribute("cy", String(y));
  circle.setAttribute("r", "2.25");
  circle.setAttribute("fill", color);
  return circle;
}

function buildBaselineLine(baseline, minValue, maxValue) {
  const y = yForValue(baseline.value, minValue, maxValue);
  const line = svgElement("line");
  line.setAttribute("class", "chart-baseline-line");
  line.setAttribute("x1", String(PAD_LEFT));
  line.setAttribute("x2", String(CHART_WIDTH - PAD_RIGHT));
  line.setAttribute("y1", String(y));
  line.setAttribute("y2", String(y));
  line.setAttribute("stroke", baseline.color);
  return line;
}

function buildHoverDot(x, y, color) {
  const circle = svgElement("circle");
  circle.setAttribute("class", "chart-hover-dot");
  circle.setAttribute("cx", String(x));
  circle.setAttribute("cy", String(y));
  circle.setAttribute("r", "4");
  circle.setAttribute("fill", color);
  return circle;
}

function buildLegendItem({ label, color }, isDashed) {
  const item = document.createElement("li");
  item.className = "legend-item";
  const swatch = document.createElement("span");
  swatch.className = `legend-swatch${isDashed ? " is-dashed" : ""}`;
  swatch.style.setProperty("--swatch-color", color);
  const text = document.createElement("span");
  text.textContent = label;
  item.append(swatch, text);
  return item;
}

function buildTooltipRow(label, valueText, color, isDashed) {
  const row = document.createElement("div");
  row.className = "chart-tooltip-row";
  const swatch = document.createElement("span");
  swatch.className = `chart-tooltip-swatch${isDashed ? " is-dashed" : ""}`;
  swatch.style.setProperty("--swatch-color", color);
  const label_ = document.createElement("span");
  label_.textContent = label;
  const value_ = document.createElement("span");
  value_.className = "chart-tooltip-value";
  value_.textContent = valueText;
  row.append(swatch, label_, value_);
  return row;
}

function buildTooltipContent(chart, index) {
  const heading = document.createElement("div");
  heading.className = "chart-tooltip-epoch";
  heading.textContent = `Epoch ${chart.epochs[index].epoch}`;
  const rows = chart.seriesConfig.map((series) => buildTooltipRow(series.label, formatValue(series.values[index]), series.color, false));
  const baselineRows = chart.baselineConfig.map((baseline) => buildTooltipRow(baseline.label, formatValue(baseline.value), baseline.color, true));
  return [heading, ...rows, ...baselineRows];
}

function makeChart(svgId) {
  const svg = document.getElementById(svgId);
  const wrap = svg.closest(".chart-wrap");
  return {
    wrap,
    svg,
    grid: svg.querySelector('[data-role="grid"]'),
    baselines: svg.querySelector('[data-role="baselines"]'),
    series: svg.querySelector('[data-role="series"]'),
    dots: svg.querySelector('[data-role="dots"]'),
    hoverDots: svg.querySelector('[data-role="hover-dots"]'),
    crosshair: svg.querySelector('[data-role="crosshair"]'),
    hoverTarget: svg.querySelector('[data-role="hover-target"]'),
    tooltip: wrap.querySelector('[data-role="tooltip"]'),
    epochs: [],
    seriesConfig: [],
    baselineConfig: [],
    domain: [0, 1],
  };
}

function renderChart(chart, epochs, seriesConfig, domain, baselineConfig) {
  chart.epochs = epochs;
  chart.seriesConfig = seriesConfig;
  chart.baselineConfig = baselineConfig;
  chart.domain = domain;
  const [minValue, maxValue] = domain;
  chart.grid.replaceChildren(...buildAxisElements(epochs, minValue, maxValue));
  chart.baselines.replaceChildren(...baselineConfig.map((baseline) => buildBaselineLine(baseline, minValue, maxValue)));
  chart.series.replaceChildren(...seriesConfig.map((series) => buildLine(pointsAttribute(series.values, epochs.length, minValue, maxValue), series.color)));
  chart.dots.replaceChildren(
    ...seriesConfig.flatMap((series) =>
      series.values.map((value, index) => buildDot(xForIndex(index, epochs.length), yForValue(value, minValue, maxValue), series.color)),
    ),
  );
}

function nearestEpochIndex(chart, svgX) {
  if (chart.epochs.length <= 1) {
    return 0;
  }
  const step = PLOT_WIDTH / (chart.epochs.length - 1);
  return clamp(Math.round((svgX - PAD_LEFT) / step), 0, chart.epochs.length - 1);
}

function svgPointFromClient(chart, clientX, clientY) {
  const rect = chart.svg.getBoundingClientRect();
  return { x: ((clientX - rect.left) / rect.width) * CHART_WIDTH, y: ((clientY - rect.top) / rect.height) * CHART_HEIGHT };
}

function positionTooltip(chart, pointerEvent) {
  const wrapRect = chart.wrap.getBoundingClientRect();
  const tooltipRect = chart.tooltip.getBoundingClientRect();
  const rawLeft = pointerEvent.clientX - wrapRect.left + 14;
  const rawTop = pointerEvent.clientY - wrapRect.top + 14;
  chart.tooltip.style.left = `${clamp(rawLeft, 6, Math.max(wrapRect.width - tooltipRect.width - 6, 6))}px`;
  chart.tooltip.style.top = `${clamp(rawTop, 6, Math.max(wrapRect.height - tooltipRect.height - 6, 6))}px`;
}

function updateHoverDots(chart, index) {
  const [minValue, maxValue] = chart.domain;
  const x = xForIndex(index, chart.epochs.length);
  chart.hoverDots.replaceChildren(
    ...chart.seriesConfig.map((series) => buildHoverDot(x, yForValue(series.values[index], minValue, maxValue), series.color)),
  );
}

function handleChartHover(chart, pointerEvent) {
  if (chart.epochs.length === 0) {
    return;
  }
  const point = svgPointFromClient(chart, pointerEvent.clientX, pointerEvent.clientY);
  const index = nearestEpochIndex(chart, point.x);
  const x = xForIndex(index, chart.epochs.length);
  chart.crosshair.setAttribute("x1", String(x));
  chart.crosshair.setAttribute("x2", String(x));
  chart.crosshair.setAttribute("y1", String(PAD_TOP));
  chart.crosshair.setAttribute("y2", String(CHART_HEIGHT - PAD_BOTTOM));
  chart.crosshair.hidden = false;
  updateHoverDots(chart, index);
  chart.tooltip.replaceChildren(...buildTooltipContent(chart, index));
  chart.tooltip.hidden = false;
  positionTooltip(chart, pointerEvent);
}

function hideChartHover(chart) {
  chart.crosshair.hidden = true;
  chart.tooltip.hidden = true;
  chart.hoverDots.replaceChildren();
}

function attachHoverHandling(chart) {
  chart.hoverTarget.addEventListener("pointermove", (pointerEvent) => handleChartHover(chart, pointerEvent));
  chart.hoverTarget.addEventListener("pointerleave", () => hideChartHover(chart));
}

const lossChart = makeChart("loss-chart");
const accuracyChart = makeChart("accuracy-chart");
attachHoverHandling(lossChart);
attachHoverHandling(accuracyChart);

function renderLossChart(epochs) {
  const trainTotals = epochs.map((epoch) => sumValues(epoch.train_losses));
  const valTotals = epochs.map((epoch) => sumValues(epoch.val_losses));
  const seriesConfig = [
    { ...LOSS_SERIES[0], values: trainTotals },
    { ...LOSS_SERIES[1], values: valTotals },
  ];
  renderChart(lossChart, epochs, seriesConfig, [0, Math.max(...trainTotals, ...valTotals, 0.01)], []);
  lossLegendElement.replaceChildren(...LOSS_SERIES.map((series) => buildLegendItem(series, false)));
}

function renderAccuracyChart(epochs, baseline) {
  const seriesConfig = ACCURACY_SERIES.map((series) => ({ ...series, values: epochs.map((epoch) => epoch.val_metrics[series.key] ?? 0) }));
  const baselineConfig = baseline
    ? ACCURACY_SERIES.filter((series) => series.key in baseline).map((series) => ({ ...series, label: `${series.label} (baseline)`, value: baseline[series.key] }))
    : [];
  renderChart(accuracyChart, epochs, seriesConfig, [0, 1], baselineConfig);
  accuracyLegendElement.replaceChildren(
    ...ACCURACY_SERIES.map((series) => buildLegendItem(series, false)),
    ...baselineConfig.map((baseline_) => buildLegendItem(baseline_, true)),
  );
}

function renderStage(epochs) {
  const hasEpochs = epochs.length > 0;
  emptyStageElement.hidden = hasEpochs;
  chartsElement.hidden = !hasEpochs;
}

function renderRunTitleBar(epochs, runInfo) {
  runNameElement.textContent = runInfo.run_name ?? currentRoute.name;
  if (epochs.length === 0) {
    epochStatusElement.textContent = "";
    statusEpochElement.textContent = "";
    return;
  }
  const lastEpoch = epochs[epochs.length - 1].epoch;
  const totalEpochs = runInfo.params.epochs;
  epochStatusElement.textContent = totalEpochs ? `Epoch ${lastEpoch} of ${totalEpochs}` : `Epoch ${lastEpoch}`;
  statusEpochElement.textContent = `${epochs.length} epoch${epochs.length === 1 ? "" : "s"} logged`;
}

function renderListTitleBar(runCount) {
  runNameElement.textContent = "BookWorm Training Dashboard";
  epochStatusElement.textContent = "";
  statusEpochElement.textContent = runCount ? `${runCount} run${runCount === 1 ? "" : "s"}` : "";
}

function basename(path) {
  return path.slice(Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\")) + 1);
}

function formatParamValue(key, value) {
  return key === "model" || key === "data" ? basename(String(value)) : String(value);
}

function buildParamRow(key, value) {
  const row = document.createElement("div");
  row.className = "param-row";
  const label = document.createElement("span");
  label.className = "param-label";
  label.textContent = PARAM_LABELS[key] ?? key;
  const valueElement = document.createElement("span");
  valueElement.className = "param-value";
  valueElement.textContent = formatParamValue(key, value);
  valueElement.title = String(value);
  row.append(label, valueElement);
  return row;
}

function renderRunParams(params) {
  const knownKeys = PARAM_ORDER.filter((key) => key in params);
  runParamsElement.replaceChildren(...knownKeys.map((key) => buildParamRow(key, params[key])));
  runParamsEmptyElement.hidden = knownKeys.length > 0;
}

function renderRunView() {
  renderStage(latestEpochs);
  renderRunTitleBar(latestEpochs, latestRunInfo);
  renderRunParams(latestRunInfo.params);
  if (latestEpochs.length > 0) {
    renderLossChart(latestEpochs);
    renderAccuracyChart(latestEpochs, latestRunInfo.baseline);
  }
}

function markUpdated() {
  statusPollElement.textContent = `updated ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
}

function formatRelativeTime(epochSeconds) {
  const deltaSeconds = Math.max(0, Date.now() / 1000 - epochSeconds);
  if (deltaSeconds < 60) {
    return "just now";
  }
  if (deltaSeconds < 3600) {
    return `${Math.floor(deltaSeconds / 60)}m ago`;
  }
  if (deltaSeconds < 86400) {
    return `${Math.floor(deltaSeconds / 3600)}h ago`;
  }
  return `${Math.floor(deltaSeconds / 86400)}d ago`;
}

function buildRunProgressText(run) {
  return run.total_epochs
    ? `epoch ${run.last_epoch} of ${run.total_epochs}`
    : `${run.epoch_count} epoch${run.epoch_count === 1 ? "" : "s"}`;
}

function buildRunRow(run) {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "run-row";
  const name = document.createElement("span");
  name.className = "run-row-name";
  name.textContent = run.name;
  const progress = document.createElement("span");
  progress.className = "run-row-meta";
  progress.textContent = buildRunProgressText(run);
  const updated = document.createElement("span");
  updated.className = "run-row-meta";
  updated.textContent = formatRelativeTime(run.updated_at);
  button.append(name, progress, updated);
  button.addEventListener("click", () => navigateToRun(run.name));
  item.append(button);
  return item;
}

function renderRunsList(runs) {
  const hasRuns = runs.length > 0;
  runsEmptyElement.hidden = hasRuns;
  runsListElement.hidden = !hasRuns;
  runsListElement.replaceChildren(...runs.map(buildRunRow));
  renderListTitleBar(runs.length);
}

function parseRoute() {
  const match = window.location.hash.match(/^#\/run\/(.+)$/);
  return match ? { view: "run", name: decodeURIComponent(match[1]) } : { view: "list" };
}

function navigateToRun(name) {
  window.location.hash = `#/run/${encodeURIComponent(name)}`;
}

function navigateToList() {
  window.location.hash = "";
}

async function fetchRuns() {
  const response = await fetch("/api/runs");
  return response.ok ? response.json() : [];
}

async function fetchMetrics(runName) {
  const query = runName ? `?run=${encodeURIComponent(runName)}` : "";
  const response = await fetch(`/api/metrics${query}`);
  return response.ok ? response.json() : [];
}

async function fetchRunInfo(runName) {
  const query = runName ? `?run=${encodeURIComponent(runName)}` : "";
  const response = await fetch(`/api/run-info${query}`);
  return response.ok ? response.json() : { run_name: null, params: {}, baseline: null };
}

async function pollRunsList() {
  renderRunsList(await fetchRuns());
  markUpdated();
}

async function pollMetrics() {
  latestEpochs = await fetchMetrics(currentRoute.name);
  renderRunView();
  markUpdated();
}

async function pollRunInfo() {
  latestRunInfo = await fetchRunInfo(currentRoute.name);
  renderRunView();
}

function pollDashboard() {
  if (currentRoute.view === "list") {
    pollRunsList().catch(() => {
      statusPollElement.textContent = "Could not reach the dashboard server";
    });
    return;
  }
  pollMetrics().catch(() => {
    statusPollElement.textContent = "Could not reach the dashboard server";
  });
  pollRunInfo().catch(() => {});
}

function applyRoute() {
  currentRoute = parseRoute();
  const isRunView = currentRoute.view === "run";
  viewListElement.hidden = isRunView;
  viewRunElement.hidden = !isRunView;
  runPaneElement.hidden = !isRunView;
  backButtonElement.hidden = !isRunView;
  appWindowElement.classList.toggle("list-view", !isRunView);
  if (isRunView) {
    latestEpochs = [];
    latestRunInfo = { run_name: null, params: {}, baseline: null };
    renderRunView();
  }
  pollDashboard();
}

backButtonElement.addEventListener("click", navigateToList);
window.addEventListener("hashchange", applyRoute);
applyRoute();
window.setInterval(pollDashboard, POLL_INTERVAL_MILLISECONDS);
