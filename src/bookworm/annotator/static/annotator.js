const KIND_SHORTCUTS = [
  { kind: "isbn", key: "1" },
  { kind: "cover", key: "2" },
  { kind: "unknown", key: "3" },
];

const BOX_TYPE_SHORTCUTS = [
  { boxType: "book", key: "b", color: "#9fc9a2" },
  { boxType: "barcode", key: "c", color: "#e59a7c" },
  { boxType: "printed_isbn", key: "i", color: "#e6c07b" },
  { boxType: "title", key: "t", color: "#9fbbe0" },
  { boxType: "author", key: "a", color: "#c0a8dd" },
  { boxType: "publisher", key: "p", color: "#e5a0c0" },
  { boxType: "other_text", key: "o", color: "#b9b4a7" },
];

const BOX_TYPES_WITHOUT_TEXT = new Set(["barcode"]);
const MIN_DRAWN_BOX_CANVAS_PIXELS = 4;
const RESIZE_HANDLE_HIT_RADIUS_CANVAS_PIXELS = 6;
const WELL_PADDING_PIXELS = 12;
const CHIP_HEIGHT_PIXELS = 18;
const CHIP_PADDING_PIXELS = 6;
const CHIP_GAP_PIXELS = 4;
const CHIP_TEXT_MAX_LENGTH = 24;
const CANVAS_GROUND_COLOR = "#14120b";
const CANVAS_LABEL_FONT = '500 11px system-ui, -apple-system, "Helvetica Neue", sans-serif';
const APP_NAME = "BookWorm Annotator";
const TEXT_FIELD_TAGS = new Set(["INPUT", "SELECT", "TEXTAREA"]);
const TIMER_REFRESH_MILLISECONDS = 1000;

const ICONS = {
  labeled: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.25"/><path d="m5.4 8.2 1.8 1.8 3.4-3.6"/></svg>',
  toLabel: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.25" stroke-dasharray="2.4 2.2"/></svg>',
  remove: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4.75 4.75 6.5 6.5m0-6.5-6.5 6.5"/></svg>',
  problem: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.25"/><path d="M8 4.9v3.7m0 2.5v.05"/></svg>',
};

const progressCountElement = document.getElementById("progress-count");
const toLabelListElement = document.getElementById("to-label-list");
const labeledListElement = document.getElementById("labeled-list");
const toLabelCountElement = document.getElementById("to-label-count");
const labeledCountElement = document.getElementById("labeled-count");
const currentPhotoElement = document.getElementById("current-photo");
const photoSizeElement = document.getElementById("photo-size");
const saveStatusElement = document.getElementById("save-status");
const photoWellElement = document.getElementById("photo-well");
const canvasFrameElement = document.getElementById("canvas-frame");
const canvasElement = document.getElementById("box-canvas");
const photoElement = buildPhotoElement();
const emptyStageElement = document.getElementById("empty-stage");
const emptyStageTitleElement = document.getElementById("empty-stage-title");
const emptyStageHintElement = document.getElementById("empty-stage-hint");
const kindButtonsElement = document.getElementById("kind-buttons");
const boxTypeButtonsElement = document.getElementById("box-type-buttons");
const boxListElement = document.getElementById("box-list");
const boxCountElement = document.getElementById("box-count");
const problemListElement = document.getElementById("problem-list");
const saveButtonElement = document.getElementById("save-button");
const saveLabelElement = document.getElementById("save-label");
const detectButtonElement = document.getElementById("detect-button");
const detectLabelElement = document.getElementById("detect-label");
const statusModeElement = document.getElementById("status-mode");
const statusEditModeElement = document.getElementById("status-edit-mode");
const statusTypeElement = document.getElementById("status-type");
const statusCursorElement = document.getElementById("status-cursor");
const statusTimerElement = document.getElementById("status-timer");

const state = {
  photos: [],
  photoPath: null,
  photoWidth: 0,
  photoHeight: 0,
  isLoadingPhoto: false,
  kind: null,
  boxType: "title",
  boxes: [],
  selectedBoxIndex: null,
  editMode: "normal",
  drag: null,
  cursorPoint: null,
  openedAt: 0,
  hasUnsavedChanges: false,
  isSaving: false,
  isDetecting: false,
};

function buildPhotoElement() {
  const photo = new Image();
  photo.id = "photo";
  photo.alt = "";
  photo.draggable = false;
  canvasFrameElement.prepend(photo);
  return photo;
}

function colorForBoxType(boxType) {
  return BOX_TYPE_SHORTCUTS.find((shortcut) => shortcut.boxType === boxType).color;
}

function boxTypeTakesText(boxType) {
  return !BOX_TYPES_WITHOUT_TEXT.has(boxType);
}

function withAlpha(hexColor, alpha) {
  const red = parseInt(hexColor.slice(1, 3), 16);
  const green = parseInt(hexColor.slice(3, 5), 16);
  const blue = parseInt(hexColor.slice(5, 7), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function truncateText(text, maxLength) {
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
}

function fileNameOf(photoPath) {
  return photoPath.slice(photoPath.lastIndexOf("/") + 1);
}

function formatDuration(milliseconds) {
  const totalSeconds = Math.floor(milliseconds / 1000);
  return `${Math.floor(totalSeconds / 60)}:${String(totalSeconds % 60).padStart(2, "0")}`;
}

function formatSavedTime(isoTimestamp) {
  return new Date(isoTimestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatBoxCoordinates(box) {
  return `${box.x_min}, ${box.y_min}  ${box.x_max - box.x_min}×${box.y_max - box.y_min}`;
}

function formatQueueMeta(photo) {
  const boxWord = photo.box_count === 1 ? "box" : "boxes";
  return photo.annotated ? `${photo.box_count} ${boxWord}` : "not labeled";
}

function currentPhotoScale() {
  return photoElement.clientWidth === 0 ? 1 : state.photoWidth / photoElement.clientWidth;
}

function toPhotoPixels(canvasPoint, scale) {
  return {
    x: clamp(Math.round(canvasPoint.x * scale), 0, state.photoWidth),
    y: clamp(Math.round(canvasPoint.y * scale), 0, state.photoHeight),
  };
}

function toCanvasPoint(photoPoint, scale) {
  return { x: photoPoint.x / scale, y: photoPoint.y / scale };
}

function toCanvasPixels(photoBox, scale) {
  return {
    x: photoBox.x_min / scale,
    y: photoBox.y_min / scale,
    width: (photoBox.x_max - photoBox.x_min) / scale,
    height: (photoBox.y_max - photoBox.y_min) / scale,
  };
}

function pointerToPhotoPixels(pointerEvent) {
  const canvasRectangle = canvasElement.getBoundingClientRect();
  const canvasPoint = { x: pointerEvent.clientX - canvasRectangle.left, y: pointerEvent.clientY - canvasRectangle.top };
  return toPhotoPixels(canvasPoint, currentPhotoScale());
}

function boxContains(outerBox, innerBox) {
  return outerBox.x_min <= innerBox.x_min && outerBox.y_min <= innerBox.y_min && outerBox.x_max >= innerBox.x_max && outerBox.y_max >= innerBox.y_max;
}

function rectanglesOverlap(first, second) {
  return first.x < second.x + second.width && second.x < first.x + first.width && first.y < second.y + second.height && second.y < first.y + first.height;
}

function moveBoxInsidePhoto(originalBox, offsetX, offsetY) {
  const width = originalBox.x_max - originalBox.x_min;
  const height = originalBox.y_max - originalBox.y_min;
  const x_min = clamp(originalBox.x_min + offsetX, 0, state.photoWidth - width);
  const y_min = clamp(originalBox.y_min + offsetY, 0, state.photoHeight - height);
  return { x_min, y_min, x_max: x_min + width, y_max: y_min + height };
}

function findTopBoxIndexAt(photoPoint) {
  return state.boxes.findLastIndex(
    ({ box }) => photoPoint.x >= box.x_min && photoPoint.x <= box.x_max && photoPoint.y >= box.y_min && photoPoint.y <= box.y_max,
  );
}

function resizeHandleAtPointer(photoPoint, boxIndex, scale) {
  const rectangle = toCanvasPixels(state.boxes[boxIndex].box, scale);
  const canvasPoint = toCanvasPoint(photoPoint, scale);
  return findResizeHandle(canvasPoint, rectangle, RESIZE_HANDLE_HIT_RADIUS_CANVAS_PIXELS);
}

function isDrawnBoxBigEnough(photoBox) {
  const canvasRectangle = toCanvasPixels(photoBox, currentPhotoScale());
  return canvasRectangle.width >= MIN_DRAWN_BOX_CANVAS_PIXELS && canvasRectangle.height >= MIN_DRAWN_BOX_CANVAS_PIXELS;
}

function describeMode() {
  if (state.photoPath === null) {
    return "Browse";
  }
  return state.kind === null ? "Classify" : "Label";
}

function setSaveStatus(text, tone) {
  saveStatusElement.textContent = text;
  saveStatusElement.dataset.tone = tone;
}

function markChanged() {
  state.hasUnsavedChanges = true;
  setSaveStatus("Unsaved changes", "unsaved");
}

async function fetchPhotos() {
  const response = await fetch("/api/photos");
  state.photos = await response.json();
  renderPhotoList();
}

async function fetchSavedAnnotation(photoPath) {
  const response = await fetch(`/api/annotation?photo=${encodeURIComponent(photoPath)}`);
  return response.ok ? response.json() : null;
}

async function fetchDetections(photoPath) {
  const response = await fetch(`/api/detections?photo=${encodeURIComponent(photoPath)}`);
  if (!response.ok) {
    throw new Error(`Detection request for ${photoPath} failed with status ${response.status}`);
  }
  return response.json();
}

async function showPhotoImage(photoPath) {
  photoElement.src = `/api/image?photo=${encodeURIComponent(photoPath)}`;
  await photoElement.decode();
  state.photoWidth = photoElement.naturalWidth;
  state.photoHeight = photoElement.naturalHeight;
}

function resetPhotoState(photoPath) {
  state.photoPath = photoPath;
  state.photoWidth = 0;
  state.photoHeight = 0;
  state.isLoadingPhoto = true;
  state.kind = null;
  state.boxes = [];
  state.selectedBoxIndex = null;
  state.editMode = "normal";
  state.drag = null;
  state.cursorPoint = null;
  state.hasUnsavedChanges = false;
  setSaveStatus("", "idle");
  showProblems([]);
}

function applySavedAnnotation(annotation) {
  state.kind = annotation?.kind ?? null;
  state.boxes = annotation?.boxes ?? [];
  setSaveStatus(annotation ? `Saved ${formatSavedTime(annotation.saved_at)}` : "Not labeled yet", annotation ? "saved" : "idle");
}

async function openPhoto(photoPath) {
  if (state.hasUnsavedChanges && !window.confirm("Discard unsaved changes to this photo?")) {
    return;
  }
  resetPhotoState(photoPath);
  renderAll();
  await showPhotoImage(photoPath);
  applySavedAnnotation(await fetchSavedAnnotation(photoPath));
  state.isLoadingPhoto = false;
  state.openedAt = performance.now();
  renderAll();
}

function markPhotoLoadFailed(photoPath) {
  state.isLoadingPhoto = false;
  setSaveStatus("", "idle");
  renderAll();
  showProblems([`Could not load ${photoPath}. Check that the file is a readable photo.`]);
}

function openPhotoAndReportFailure(photoPath) {
  openPhoto(photoPath).catch(() => markPhotoLoadFailed(photoPath));
}

function openNextPhoto() {
  const currentIndex = state.photos.findIndex((photo) => photo.photo_path === state.photoPath);
  const nextPhoto = state.photos[currentIndex + 1];
  if (nextPhoto) {
    openPhotoAndReportFailure(nextPhoto.photo_path);
  }
}

function buildDraft() {
  return {
    photo_path: state.photoPath,
    photo_width: state.photoWidth,
    photo_height: state.photoHeight,
    kind: state.kind,
    boxes: state.boxes,
    labeling_duration_ms: Math.round(performance.now() - state.openedAt),
  };
}

function describeRequestValidationErrors(responseBody) {
  return (responseBody.detail ?? []).map((error) => `${error.loc.join(".")}: ${error.msg}`);
}

function setSaving(isSaving) {
  state.isSaving = isSaving;
  saveButtonElement.disabled = isSaving;
  saveLabelElement.textContent = isSaving ? "Saving…" : "Save";
}

function setDetecting(isDetecting) {
  state.isDetecting = isDetecting;
  detectLabelElement.textContent = isDetecting ? "Detecting…" : "Detect boxes";
  renderStage();
}

function putDraft(draft) {
  return fetch("/api/annotation", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(draft),
  });
}

function markCurrentPhotoLabeled() {
  const currentPhoto = state.photos.find((photo) => photo.photo_path === state.photoPath);
  currentPhoto.annotated = true;
  currentPhoto.box_count = state.boxes.length;
}

async function saveAnnotation() {
  if (state.photoPath === null || state.kind === null) {
    showProblems(["Pick a photo and a class before saving."]);
    return;
  }
  setSaving(true);
  const response = await putDraft(buildDraft()).finally(() => setSaving(false));
  const responseBody = await response.json();
  if (!response.ok) {
    showProblems(responseBody.problems ?? describeRequestValidationErrors(responseBody));
    return;
  }
  state.hasUnsavedChanges = false;
  setSaveStatus(`Saved ${formatSavedTime(responseBody.saved_at)}`, "saved");
  showProblems([]);
  markCurrentPhotoLabeled();
  renderPhotoList();
}

function saveAnnotationAndReportFailure() {
  saveAnnotation().catch(() => showProblems(["Could not reach the annotator server. Is `bookworm annotator` still running?"]));
}

async function detectBoxes() {
  const photoPath = state.photoPath;
  setDetecting(true);
  const detections = await fetchDetections(photoPath).finally(() => setDetecting(false));
  if (state.photoPath !== photoPath) {
    return;
  }
  state.boxes.push(...detections);
  markChanged();
  renderAll();
}

function detectBoxesAndReportFailure() {
  detectBoxes().catch(() => showProblems(["Could not reach the annotator server. Is `bookworm annotator` still running?"]));
}

function selectKind(kind) {
  state.kind = kind;
  markChanged();
  renderAll();
}

function selectBoxType(boxType) {
  state.boxType = boxType;
  renderShortcutButtons();
  renderStatusBar();
  renderBoxList();
}

function toggleEditMode() {
  state.editMode = state.editMode === "insert" ? "normal" : "insert";
  renderAll();
}

function forceNormalMode() {
  state.drag = null;
  state.editMode = "normal";
  renderAll();
}

function deleteSelectedBox() {
  if (state.selectedBoxIndex === null) {
    return;
  }
  state.boxes.splice(state.selectedBoxIndex, 1);
  state.selectedBoxIndex = null;
  markChanged();
  renderAll();
}

function changeBoxType(labeledBox, boxType) {
  labeledBox.box_type = boxType;
  labeledBox.text = boxTypeTakesText(boxType) ? labeledBox.text : "";
  markChanged();
  renderAll();
}

function buildIcon(iconName, className) {
  const iconElement = document.createElement("span");
  iconElement.className = className;
  iconElement.innerHTML = ICONS[iconName];
  return iconElement;
}

function buildSwatch(color) {
  const swatch = document.createElement("span");
  swatch.className = "type-swatch";
  swatch.style.setProperty("--type-color", color);
  return swatch;
}

function buildKeyedButton({ label, key, isActive, className, onClick }) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = className;
  button.setAttribute("aria-pressed", String(isActive));
  const labelElement = document.createElement("span");
  labelElement.className = "option-label";
  labelElement.textContent = label;
  const keyElement = document.createElement("kbd");
  keyElement.textContent = key;
  button.append(labelElement, keyElement);
  button.addEventListener("click", onClick);
  return button;
}

function buildBoxTypeButton({ boxType, key, color }) {
  const button = buildKeyedButton({
    label: boxType,
    key,
    isActive: state.boxType === boxType,
    className: "type-option",
    onClick: () => selectBoxType(boxType),
  });
  button.style.setProperty("--type-color", color);
  button.prepend(buildSwatch(color));
  return button;
}

function renderShortcutButtons() {
  kindButtonsElement.replaceChildren(
    ...KIND_SHORTCUTS.map(({ kind, key }) =>
      buildKeyedButton({ label: kind, key, isActive: state.kind === kind, className: "segment", onClick: () => selectKind(kind) }),
    ),
  );
  boxTypeButtonsElement.replaceChildren(...BOX_TYPE_SHORTCUTS.map(buildBoxTypeButton));
}

function buildPhotoListItem(photo) {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "queue-row";
  button.title = photo.photo_path;
  button.classList.toggle("current", photo.photo_path === state.photoPath);
  button.setAttribute("aria-current", String(photo.photo_path === state.photoPath));
  const nameElement = document.createElement("span");
  nameElement.className = "queue-name";
  nameElement.textContent = fileNameOf(photo.photo_path);
  const metaElement = document.createElement("span");
  metaElement.className = "queue-meta";
  metaElement.textContent = formatQueueMeta(photo);
  button.append(buildIcon(photo.annotated ? "labeled" : "toLabel", `queue-icon${photo.annotated ? " is-labeled" : ""}`), nameElement, metaElement);
  button.addEventListener("click", () => openPhotoAndReportFailure(photo.photo_path));
  item.append(button);
  return item;
}

function buildQueueNote(text) {
  const item = document.createElement("li");
  item.className = "queue-note";
  item.textContent = text;
  return item;
}

function renderProgressCount(labeledCount, totalCount) {
  const longText = document.createElement("span");
  longText.className = "progress-long";
  longText.textContent = `${labeledCount} of ${totalCount} labeled`;
  const shortText = document.createElement("span");
  shortText.className = "progress-short";
  shortText.setAttribute("aria-hidden", "true");
  shortText.textContent = `${labeledCount}/${totalCount}`;
  progressCountElement.replaceChildren(longText, shortText);
}

function renderPhotoList() {
  const photosToLabel = state.photos.filter((photo) => !photo.annotated);
  const labeledPhotos = state.photos.filter((photo) => photo.annotated);
  toLabelListElement.replaceChildren(...(photosToLabel.length ? photosToLabel.map(buildPhotoListItem) : [buildQueueNote("Nothing left to label")]));
  labeledListElement.replaceChildren(...(labeledPhotos.length ? labeledPhotos.map(buildPhotoListItem) : [buildQueueNote("Saved photos appear here")]));
  toLabelCountElement.textContent = String(photosToLabel.length);
  labeledCountElement.textContent = String(labeledPhotos.length);
  renderProgressCount(labeledPhotos.length, state.photos.length);
}

function buildBoxTypeSelect(labeledBox) {
  const picker = document.createElement("span");
  picker.className = "box-type-picker";
  const select = document.createElement("select");
  select.className = "box-type-select";
  select.setAttribute("aria-label", "Box type");
  BOX_TYPE_SHORTCUTS.forEach(({ boxType }) => select.append(new Option(boxType, boxType, false, boxType === labeledBox.box_type)));
  select.addEventListener("change", () => changeBoxType(labeledBox, select.value));
  picker.append(select);
  return picker;
}

function buildBoxTextInput(labeledBox) {
  const input = document.createElement("input");
  input.type = "text";
  input.className = "box-text-input";
  input.value = labeledBox.text;
  input.placeholder = labeledBox.box_type === "book" ? "Text on the book (optional)" : "Text inside the box";
  input.setAttribute("aria-label", `Text for ${labeledBox.box_type} box`);
  input.addEventListener("input", () => {
    labeledBox.text = input.value;
    markChanged();
  });
  return input;
}

function buildNoTextNote() {
  const note = document.createElement("span");
  note.className = "no-text";
  note.textContent = "Barcode boxes have no text";
  return note;
}

function buildDeleteBoxButton(boxIndex) {
  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.className = "icon-button";
  deleteButton.title = "Delete box";
  deleteButton.setAttribute("aria-label", "Delete box");
  deleteButton.innerHTML = ICONS.remove;
  deleteButton.addEventListener("click", () => {
    state.selectedBoxIndex = boxIndex;
    deleteSelectedBox();
  });
  return deleteButton;
}

function buildBoxListItem(labeledBox, boxIndex) {
  const item = document.createElement("li");
  item.className = "box-row";
  item.classList.toggle("selected", boxIndex === state.selectedBoxIndex);
  item.style.setProperty("--type-color", colorForBoxType(labeledBox.box_type));
  item.addEventListener("focusin", () => {
    state.selectedBoxIndex = boxIndex;
    renderCanvas();
  });
  const head = document.createElement("div");
  head.className = "box-row-head";
  const coordinates = document.createElement("span");
  coordinates.className = "box-coordinates";
  coordinates.textContent = formatBoxCoordinates(labeledBox.box);
  head.append(buildSwatch(colorForBoxType(labeledBox.box_type)), buildBoxTypeSelect(labeledBox), coordinates, buildDeleteBoxButton(boxIndex));
  const textCell = boxTypeTakesText(labeledBox.box_type) ? buildBoxTextInput(labeledBox) : buildNoTextNote();
  item.append(head, textCell);
  return item;
}

function buildBoxListEmptyNote() {
  const item = document.createElement("li");
  item.className = "box-list-empty";
  const title = document.createElement("strong");
  const hint = document.createElement("span");
  title.textContent = state.photoPath === null ? "No photo open" : "No boxes yet";
  hint.textContent = state.photoPath === null ? "Open a photo to start labeling." : `Drag on the photo to draw a ${state.boxType} box.`;
  item.append(title, hint);
  return item;
}

function renderBoxList() {
  boxListElement.replaceChildren(...(state.boxes.length ? state.boxes.map(buildBoxListItem) : [buildBoxListEmptyNote()]));
  boxCountElement.textContent = state.boxes.length ? String(state.boxes.length) : "";
}

function focusBoxTextInput(boxIndex) {
  boxListElement.children[boxIndex]?.querySelector("input")?.focus();
}

function buildProblemItem(problem) {
  const item = document.createElement("li");
  item.className = "problem";
  const text = document.createElement("span");
  text.textContent = problem;
  item.append(buildIcon("problem", "problem-icon"), text);
  return item;
}

function showProblems(problems) {
  problemListElement.replaceChildren(...problems.map(buildProblemItem));
}

function renderStage() {
  const hasPhoto = state.photoWidth > 0;
  canvasFrameElement.hidden = !hasPhoto;
  emptyStageElement.hidden = hasPhoto;
  emptyStageElement.classList.toggle("is-loading", state.isLoadingPhoto);
  emptyStageTitleElement.textContent = state.isLoadingPhoto ? `Loading ${state.photoPath}…` : "Pick a photo from the list";
  emptyStageHintElement.hidden = state.isLoadingPhoto;
  currentPhotoElement.textContent = state.photoPath ?? APP_NAME;
  photoSizeElement.textContent = hasPhoto ? `${state.photoWidth} × ${state.photoHeight}` : "";
  canvasFrameElement.classList.toggle("locked", hasPhoto && state.kind === null);
  detectButtonElement.disabled = state.photoPath === null || state.kind === null || state.isDetecting;
}

function fitPhotoToWell() {
  if (state.photoWidth === 0) {
    return;
  }
  const wellRectangle = photoWellElement.getBoundingClientRect();
  const availableWidth = Math.max(wellRectangle.width - WELL_PADDING_PIXELS * 2, 0);
  const availableHeight = Math.max(wellRectangle.height - WELL_PADDING_PIXELS * 2, 0);
  const fitScale = Math.min(availableWidth / state.photoWidth, availableHeight / state.photoHeight);
  photoElement.style.width = `${Math.floor(state.photoWidth * fitScale)}px`;
  photoElement.style.height = `${Math.floor(state.photoHeight * fitScale)}px`;
}

function renderStatusCursor() {
  statusCursorElement.textContent = state.cursorPoint ? `x ${state.cursorPoint.x}  y ${state.cursorPoint.y}` : "";
}

function renderTimer() {
  statusTimerElement.textContent = state.photoWidth > 0 ? formatDuration(performance.now() - state.openedAt) : "0:00";
}

function renderStatusBar() {
  statusModeElement.textContent = describeMode();
  statusEditModeElement.textContent = state.editMode.toUpperCase();
  statusEditModeElement.classList.toggle("is-insert", state.editMode === "insert");
  statusTypeElement.textContent = state.boxType;
  statusTypeElement.style.setProperty("--type-color", colorForBoxType(state.boxType));
  renderStatusCursor();
  renderTimer();
}

function listChipObstacles(boxIndex, scale) {
  const ownBox = state.boxes[boxIndex].box;
  return state.boxes
    .filter((otherLabeledBox, otherIndex) => otherIndex !== boxIndex && !boxContains(otherLabeledBox.box, ownBox))
    .map((otherLabeledBox) => toCanvasPixels(otherLabeledBox.box, scale));
}

function isChipSpotFree(chipRectangle, obstacleRectangles) {
  const fitsInsidePhoto = chipRectangle.y >= 0 && chipRectangle.y + chipRectangle.height <= photoElement.clientHeight;
  return fitsInsidePhoto && !obstacleRectangles.some((obstacle) => rectanglesOverlap(chipRectangle, obstacle));
}

function findChipTop(rectangle, chipWidth, obstacleRectangles) {
  const outsideTops = [rectangle.y - CHIP_HEIGHT_PIXELS - CHIP_GAP_PIXELS, rectangle.y + rectangle.height + CHIP_GAP_PIXELS];
  const freeOutsideTop = outsideTops.find((top) =>
    isChipSpotFree({ x: rectangle.x, y: top, width: chipWidth, height: CHIP_HEIGHT_PIXELS }, obstacleRectangles),
  );
  return freeOutsideTop ?? rectangle.y + CHIP_GAP_PIXELS;
}

function drawBoxChip(context, text, color, rectangle, obstacleRectangles) {
  context.font = CANVAS_LABEL_FONT;
  const chipWidth = Math.ceil(context.measureText(text).width) + CHIP_PADDING_PIXELS * 2;
  const chipTop = findChipTop(rectangle, chipWidth, obstacleRectangles);
  context.fillStyle = color;
  context.beginPath();
  context.roundRect(rectangle.x, chipTop, chipWidth, CHIP_HEIGHT_PIXELS, 4);
  context.fill();
  context.fillStyle = CANVAS_GROUND_COLOR;
  context.textBaseline = "middle";
  context.fillText(text, rectangle.x + CHIP_PADDING_PIXELS, chipTop + CHIP_HEIGHT_PIXELS / 2 + 0.5);
}

function describeBoxChip(labeledBox, isSelected) {
  return isSelected && labeledBox.text ? `${labeledBox.box_type} · ${truncateText(labeledBox.text, CHIP_TEXT_MAX_LENGTH)}` : labeledBox.box_type;
}

function drawResizeHandles(context, rectangle, color) {
  context.lineWidth = 1.5;
  context.strokeStyle = color;
  context.fillStyle = CANVAS_GROUND_COLOR;
  RESIZE_HANDLES.forEach((handle) => {
    const { x, y } = resizeHandleCanvasPoint(handle, rectangle);
    context.fillRect(x - 3, y - 3, 6, 6);
    context.strokeRect(x - 3, y - 3, 6, 6);
  });
}

function drawLabeledBox(context, { labeledBox, boxIndex, isSelected }, scale) {
  const rectangle = toCanvasPixels(labeledBox.box, scale);
  const color = colorForBoxType(labeledBox.box_type);
  const lineWidth = isSelected ? 2.5 : 1.5;
  if (!labeledBox.confirmed) {
    context.setLineDash([6, 4]);
  }
  context.lineWidth = lineWidth + 2;
  context.strokeStyle = "rgba(20, 18, 11, 0.6)";
  context.strokeRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height);
  context.lineWidth = lineWidth;
  context.strokeStyle = color;
  context.strokeRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height);
  context.setLineDash([]);
  if (isSelected) {
    context.fillStyle = withAlpha(color, 0.12);
    context.fillRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height);
    drawResizeHandles(context, rectangle, color);
  }
  drawBoxChip(context, describeBoxChip(labeledBox, isSelected), color, rectangle, listChipObstacles(boxIndex, scale));
}

function drawBoxBeingDrawn(context, photoBox, scale) {
  const rectangle = toCanvasPixels(photoBox, scale);
  const color = colorForBoxType(state.boxType);
  context.setLineDash([6, 4]);
  context.lineWidth = 1.5;
  context.strokeStyle = color;
  context.fillStyle = withAlpha(color, 0.1);
  context.fillRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height);
  context.strokeRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height);
  context.setLineDash([]);
}

function listBoxesInDrawOrder() {
  const drawEntries = state.boxes.map((labeledBox, boxIndex) => ({ labeledBox, boxIndex, isSelected: boxIndex === state.selectedBoxIndex }));
  return [...drawEntries.filter((entry) => !entry.isSelected), ...drawEntries.filter((entry) => entry.isSelected)];
}

function shouldShowCrosshair() {
  return state.cursorPoint !== null && state.kind !== null && state.drag === null;
}

function drawCrosshair(context, canvasPoint, width, height) {
  context.setLineDash([3, 4]);
  context.lineWidth = 1;
  context.strokeStyle = withAlpha(colorForBoxType(state.boxType), 0.75);
  context.beginPath();
  context.moveTo(Math.round(canvasPoint.x) + 0.5, 0);
  context.lineTo(Math.round(canvasPoint.x) + 0.5, height);
  context.moveTo(0, Math.round(canvasPoint.y) + 0.5);
  context.lineTo(width, Math.round(canvasPoint.y) + 0.5);
  context.stroke();
  context.setLineDash([]);
}

function renderCanvas() {
  const displayWidth = photoElement.clientWidth;
  const displayHeight = photoElement.clientHeight;
  const pixelRatio = window.devicePixelRatio || 1;
  canvasElement.width = Math.round(displayWidth * pixelRatio);
  canvasElement.height = Math.round(displayHeight * pixelRatio);
  canvasElement.style.width = `${displayWidth}px`;
  canvasElement.style.height = `${displayHeight}px`;
  const context = canvasElement.getContext("2d");
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  const scale = currentPhotoScale();
  if (shouldShowCrosshair()) {
    drawCrosshair(context, toCanvasPoint(state.cursorPoint, scale), displayWidth, displayHeight);
  }
  listBoxesInDrawOrder().forEach((drawEntry) => drawLabeledBox(context, drawEntry, scale));
  if (state.drag?.mode === "draw") {
    drawBoxBeingDrawn(context, boxFromCorners(state.drag.startPoint, state.drag.currentPoint), scale);
  }
}

function renderAll() {
  renderStage();
  fitPhotoToWell();
  renderPhotoList();
  renderShortcutButtons();
  renderBoxList();
  renderStatusBar();
  renderCanvas();
}

function startDrag(pointerEvent) {
  if (state.photoPath === null || state.kind === null) {
    return;
  }
  const photoPoint = pointerToPhotoPixels(pointerEvent);
  const scale = currentPhotoScale();
  const resizeHandle = state.selectedBoxIndex === null ? null : resizeHandleAtPointer(photoPoint, state.selectedBoxIndex, scale);
  const boxIndex = findTopBoxIndexAt(photoPoint);
  const dragMode = chooseDragMode({ editMode: state.editMode, selectedBoxIndex: state.selectedBoxIndex, resizeHandle, boxIndexAtPoint: boxIndex });
  canvasElement.setPointerCapture(pointerEvent.pointerId);
  if (dragMode === "resize") {
    state.drag = { mode: "resize", handle: resizeHandle, boxIndex: state.selectedBoxIndex, originalBox: { ...state.boxes[state.selectedBoxIndex].box } };
    renderAll();
    return;
  }
  state.selectedBoxIndex = boxIndex === -1 ? null : boxIndex;
  state.drag =
    dragMode === "draw"
      ? { mode: "draw", startPoint: photoPoint, currentPoint: photoPoint }
      : { mode: "move", startPoint: photoPoint, boxIndex, originalBox: { ...state.boxes[boxIndex].box } };
  renderAll();
}

function trackCursor(pointerEvent) {
  if (state.photoWidth === 0) {
    return;
  }
  state.cursorPoint = pointerToPhotoPixels(pointerEvent);
  renderStatusCursor();
  if (state.drag === null) {
    renderCanvas();
  }
}

function clearCursor() {
  state.cursorPoint = null;
  renderStatusCursor();
  renderCanvas();
}

function continueDrag(pointerEvent) {
  if (state.drag === null) {
    return;
  }
  const photoPoint = pointerToPhotoPixels(pointerEvent);
  if (state.drag.mode === "draw") {
    state.drag.currentPoint = photoPoint;
  } else if (state.drag.mode === "resize") {
    state.boxes[state.drag.boxIndex].box = resizeBox(state.drag.originalBox, state.drag.handle, photoPoint);
    markChanged();
  } else {
    const offsetX = photoPoint.x - state.drag.startPoint.x;
    const offsetY = photoPoint.y - state.drag.startPoint.y;
    state.boxes[state.drag.boxIndex].box = moveBoxInsidePhoto(state.drag.originalBox, offsetX, offsetY);
    markChanged();
  }
  renderCanvas();
}

function finishDrag() {
  if (state.drag === null) {
    return;
  }
  const finishedDrag = state.drag;
  state.drag = null;
  const addedBox = finishedDrag.mode === "draw" && addDrawnBox(boxFromCorners(finishedDrag.startPoint, finishedDrag.currentPoint));
  renderAll();
  if (addedBox) {
    focusBoxTextInput(state.selectedBoxIndex);
  }
}

function addDrawnBox(photoBox) {
  if (!isDrawnBoxBigEnough(photoBox)) {
    return false;
  }
  state.boxes.push({ box_type: state.boxType, box: photoBox, text: "", confirmed: true });
  state.selectedBoxIndex = state.boxes.length - 1;
  markChanged();
  return true;
}

function isTypingInTextField(keyboardEvent) {
  return TEXT_FIELD_TAGS.has(keyboardEvent.target.tagName);
}

function handleKeyDown(keyboardEvent) {
  const isSaveShortcut = (keyboardEvent.metaKey || keyboardEvent.ctrlKey) && keyboardEvent.key.toLowerCase() === "s";
  if (isSaveShortcut) {
    keyboardEvent.preventDefault();
    saveAnnotationAndReportFailure();
    return;
  }
  if (isTypingInTextField(keyboardEvent) && (keyboardEvent.key === "Enter" || keyboardEvent.key === "Escape")) {
    keyboardEvent.target.blur();
    return;
  }
  if (isTypingInTextField(keyboardEvent) || keyboardEvent.metaKey || keyboardEvent.ctrlKey || keyboardEvent.altKey) {
    return;
  }
  handleShortcutKey(keyboardEvent);
}

function handleShortcutKey(keyboardEvent) {
  const key = keyboardEvent.key.toLowerCase();
  const kindShortcut = KIND_SHORTCUTS.find((shortcut) => shortcut.key === key);
  const boxTypeShortcut = BOX_TYPE_SHORTCUTS.find((shortcut) => shortcut.key === key);
  const actions = {
    delete: deleteSelectedBox,
    backspace: deleteSelectedBox,
    n: openNextPhoto,
    tab: toggleEditMode,
    escape: forceNormalMode,
  };
  if (kindShortcut) {
    selectKind(kindShortcut.kind);
  } else if (boxTypeShortcut) {
    selectBoxType(boxTypeShortcut.boxType);
  } else if (actions[key]) {
    keyboardEvent.preventDefault();
    actions[key]();
  }
}

function handleWindowResize() {
  fitPhotoToWell();
  renderCanvas();
}

canvasElement.addEventListener("pointerdown", startDrag);
canvasElement.addEventListener("pointermove", trackCursor);
canvasElement.addEventListener("pointermove", continueDrag);
canvasElement.addEventListener("pointerup", finishDrag);
canvasElement.addEventListener("pointerleave", clearCursor);
saveButtonElement.addEventListener("click", saveAnnotationAndReportFailure);
detectButtonElement.addEventListener("click", detectBoxesAndReportFailure);
document.addEventListener("keydown", handleKeyDown);
window.addEventListener("resize", handleWindowResize);
window.addEventListener("beforeunload", (unloadEvent) => {
  if (state.hasUnsavedChanges) {
    unloadEvent.preventDefault();
  }
});
window.setInterval(renderTimer, TIMER_REFRESH_MILLISECONDS);

renderAll();
fetchPhotos();
