const KIND_SHORTCUTS = [
  { kind: "isbn", key: "1" },
  { kind: "cover", key: "2" },
  { kind: "unknown", key: "3" },
];

const BOX_TYPE_SHORTCUTS = [
  { boxType: "book", key: "b", color: "#1f9d55" },
  { boxType: "barcode", key: "c", color: "#e3342f" },
  { boxType: "printed_isbn", key: "i", color: "#f08c00" },
  { boxType: "title", key: "t", color: "#1c7ed6" },
  { boxType: "author", key: "a", color: "#9c36b5" },
  { boxType: "publisher", key: "p", color: "#d6336c" },
  { boxType: "other_text", key: "o", color: "#495057" },
];

const MIN_DRAWN_BOX_CANVAS_PIXELS = 4;
const TEXT_FIELD_TAGS = new Set(["INPUT", "SELECT", "TEXTAREA"]);

const photoListElement = document.getElementById("photo-list");
const currentPhotoElement = document.getElementById("current-photo");
const saveStatusElement = document.getElementById("save-status");
const canvasFrameElement = document.getElementById("canvas-frame");
const photoElement = document.getElementById("photo");
const canvasElement = document.getElementById("box-canvas");
const kindButtonsElement = document.getElementById("kind-buttons");
const boxTypeButtonsElement = document.getElementById("box-type-buttons");
const boxListElement = document.getElementById("box-list");
const problemListElement = document.getElementById("problem-list");
const saveButtonElement = document.getElementById("save-button");

const state = {
  photos: [],
  photoPath: null,
  photoWidth: 0,
  photoHeight: 0,
  kind: null,
  boxType: "title",
  boxes: [],
  selectedBoxIndex: null,
  drag: null,
  openedAt: 0,
  hasUnsavedChanges: false,
};

function colorForBoxType(boxType) {
  return BOX_TYPE_SHORTCUTS.find((shortcut) => shortcut.boxType === boxType).color;
}

function currentPhotoScale() {
  return photoElement.clientWidth === 0 ? 1 : state.photoWidth / photoElement.clientWidth;
}

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function toPhotoPixels(canvasPoint, scale) {
  return {
    x: clamp(Math.round(canvasPoint.x * scale), 0, state.photoWidth),
    y: clamp(Math.round(canvasPoint.y * scale), 0, state.photoHeight),
  };
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

function boxFromCorners(startPoint, endPoint) {
  return {
    x_min: Math.min(startPoint.x, endPoint.x),
    y_min: Math.min(startPoint.y, endPoint.y),
    x_max: Math.max(startPoint.x, endPoint.x),
    y_max: Math.max(startPoint.y, endPoint.y),
  };
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

function isDrawnBoxBigEnough(photoBox) {
  const canvasRectangle = toCanvasPixels(photoBox, currentPhotoScale());
  return canvasRectangle.width >= MIN_DRAWN_BOX_CANVAS_PIXELS && canvasRectangle.height >= MIN_DRAWN_BOX_CANVAS_PIXELS;
}

function markChanged() {
  state.hasUnsavedChanges = true;
  saveStatusElement.textContent = "Unsaved changes";
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
  state.kind = null;
  state.boxes = [];
  state.selectedBoxIndex = null;
  state.drag = null;
  state.hasUnsavedChanges = false;
  saveStatusElement.textContent = "Loading…";
  showProblems([]);
}

function applySavedAnnotation(annotation) {
  state.kind = annotation?.kind ?? null;
  state.boxes = annotation?.boxes ?? [];
  saveStatusElement.textContent = annotation ? `Saved ${annotation.saved_at}` : "Not labeled yet";
}

async function openPhoto(photoPath) {
  if (state.hasUnsavedChanges && !window.confirm("Discard unsaved changes to this photo?")) {
    return;
  }
  resetPhotoState(photoPath);
  renderAll();
  await showPhotoImage(photoPath);
  applySavedAnnotation(await fetchSavedAnnotation(photoPath));
  state.openedAt = performance.now();
  renderAll();
}

function openPhotoAndReportFailure(photoPath) {
  openPhoto(photoPath).catch(() => {
    saveStatusElement.textContent = "";
    showProblems([`Could not load ${photoPath}`]);
  });
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

async function saveAnnotation() {
  if (state.photoPath === null || state.kind === null) {
    showProblems(["Pick a photo and a class before saving"]);
    return;
  }
  const response = await fetch("/api/annotation", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(buildDraft()),
  });
  const responseBody = await response.json();
  if (!response.ok) {
    showProblems(responseBody.problems ?? describeRequestValidationErrors(responseBody));
    return;
  }
  state.hasUnsavedChanges = false;
  saveStatusElement.textContent = `Saved ${responseBody.saved_at}`;
  showProblems([]);
  state.photos.find((photo) => photo.photo_path === state.photoPath).annotated = true;
  renderPhotoList();
}

function selectKind(kind) {
  state.kind = kind;
  markChanged();
  renderAll();
}

function selectBoxType(boxType) {
  state.boxType = boxType;
  renderShortcutButtons();
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

function showProblems(problems) {
  problemListElement.replaceChildren(
    ...problems.map((problem) => {
      const item = document.createElement("li");
      item.textContent = problem;
      return item;
    }),
  );
}

function buildShortcutButton(label, key, isActive, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.classList.toggle("active", isActive);
  button.append(label, " ");
  const keyElement = document.createElement("kbd");
  keyElement.textContent = key;
  button.append(keyElement);
  button.addEventListener("click", onClick);
  return button;
}

function renderShortcutButtons() {
  kindButtonsElement.replaceChildren(
    ...KIND_SHORTCUTS.map(({ kind, key }) => buildShortcutButton(kind, key, state.kind === kind, () => selectKind(kind))),
  );
  boxTypeButtonsElement.replaceChildren(
    ...BOX_TYPE_SHORTCUTS.map(({ boxType, key, color }) => {
      const button = buildShortcutButton(boxType, key, state.boxType === boxType, () => selectBoxType(boxType));
      button.style.borderLeftColor = color;
      return button;
    }),
  );
}

function buildPhotoListItem(photo) {
  const item = document.createElement("li");
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = `${photo.annotated ? "✓" : "·"} ${photo.photo_path}`;
  button.classList.toggle("current", photo.photo_path === state.photoPath);
  button.addEventListener("click", () => openPhotoAndReportFailure(photo.photo_path));
  item.append(button);
  return item;
}

function renderPhotoList() {
  photoListElement.replaceChildren(...state.photos.map(buildPhotoListItem));
}

function buildBoxTypeSelect(labeledBox) {
  const select = document.createElement("select");
  BOX_TYPE_SHORTCUTS.forEach(({ boxType }) => select.append(new Option(boxType, boxType, false, boxType === labeledBox.box_type)));
  select.addEventListener("change", () => {
    labeledBox.box_type = select.value;
    markChanged();
    renderCanvas();
  });
  return select;
}

function buildBoxTextInput(labeledBox) {
  const input = document.createElement("input");
  input.type = "text";
  input.value = labeledBox.text;
  input.placeholder = labeledBox.box_type === "book" ? "optional" : "text inside the box";
  input.addEventListener("input", () => {
    labeledBox.text = input.value;
    markChanged();
  });
  return input;
}

function buildBoxListItem(labeledBox, boxIndex) {
  const item = document.createElement("li");
  item.classList.toggle("selected", boxIndex === state.selectedBoxIndex);
  item.style.borderLeftColor = colorForBoxType(labeledBox.box_type);
  const deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.textContent = "✕";
  deleteButton.title = "Delete box";
  deleteButton.addEventListener("click", () => {
    state.selectedBoxIndex = boxIndex;
    deleteSelectedBox();
  });
  item.addEventListener("focusin", () => {
    state.selectedBoxIndex = boxIndex;
    renderCanvas();
  });
  item.append(buildBoxTypeSelect(labeledBox), buildBoxTextInput(labeledBox), deleteButton);
  return item;
}

function renderBoxList() {
  boxListElement.replaceChildren(...state.boxes.map(buildBoxListItem));
}

function focusBoxTextInput(boxIndex) {
  boxListElement.children[boxIndex]?.querySelector("input")?.focus();
}

function drawLabeledBox(context, labeledBox, scale, isSelected) {
  const rectangle = toCanvasPixels(labeledBox.box, scale);
  const color = colorForBoxType(labeledBox.box_type);
  context.lineWidth = isSelected ? 4 : 2;
  context.strokeStyle = color;
  context.strokeRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height);
  context.fillStyle = color;
  context.font = "13px system-ui, sans-serif";
  context.fillText(labeledBox.text ? `${labeledBox.box_type}: ${labeledBox.text}` : labeledBox.box_type, rectangle.x, Math.max(rectangle.y - 5, 12));
}

function drawBoxBeingDrawn(context, photoBox, scale) {
  const rectangle = toCanvasPixels(photoBox, scale);
  context.setLineDash([6, 4]);
  context.lineWidth = 2;
  context.strokeStyle = colorForBoxType(state.boxType);
  context.strokeRect(rectangle.x, rectangle.y, rectangle.width, rectangle.height);
  context.setLineDash([]);
}

function renderCanvas() {
  canvasElement.width = photoElement.clientWidth;
  canvasElement.height = photoElement.clientHeight;
  const context = canvasElement.getContext("2d");
  const scale = currentPhotoScale();
  state.boxes.forEach((labeledBox, boxIndex) => drawLabeledBox(context, labeledBox, scale, boxIndex === state.selectedBoxIndex));
  if (state.drag?.mode === "draw") {
    drawBoxBeingDrawn(context, boxFromCorners(state.drag.startPoint, state.drag.currentPoint), scale);
  }
  canvasFrameElement.classList.toggle("locked", state.photoPath !== null && state.kind === null);
}

function renderAll() {
  currentPhotoElement.textContent = state.photoPath ?? "Pick a photo on the left";
  renderPhotoList();
  renderShortcutButtons();
  renderBoxList();
  renderCanvas();
}

function startDrag(pointerEvent) {
  if (state.photoPath === null || state.kind === null) {
    return;
  }
  const photoPoint = pointerToPhotoPixels(pointerEvent);
  const boxIndex = findTopBoxIndexAt(photoPoint);
  canvasElement.setPointerCapture(pointerEvent.pointerId);
  state.selectedBoxIndex = boxIndex === -1 ? null : boxIndex;
  state.drag =
    boxIndex === -1
      ? { mode: "draw", startPoint: photoPoint, currentPoint: photoPoint }
      : { mode: "move", startPoint: photoPoint, boxIndex, originalBox: { ...state.boxes[boxIndex].box } };
  renderAll();
}

function continueDrag(pointerEvent) {
  if (state.drag === null) {
    return;
  }
  const photoPoint = pointerToPhotoPixels(pointerEvent);
  if (state.drag.mode === "draw") {
    state.drag.currentPoint = photoPoint;
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
    saveAnnotation();
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

canvasElement.addEventListener("pointerdown", startDrag);
canvasElement.addEventListener("pointermove", continueDrag);
canvasElement.addEventListener("pointerup", finishDrag);
saveButtonElement.addEventListener("click", saveAnnotation);
document.addEventListener("keydown", handleKeyDown);
window.addEventListener("resize", renderCanvas);
window.addEventListener("beforeunload", (unloadEvent) => {
  if (state.hasUnsavedChanges) {
    unloadEvent.preventDefault();
  }
});

renderAll();
fetchPhotos();
