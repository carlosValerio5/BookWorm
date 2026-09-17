const CORNER_HANDLES = [
  { id: "nw", xEdge: "x_min", yEdge: "y_min" },
  { id: "ne", xEdge: "x_max", yEdge: "y_min" },
  { id: "sw", xEdge: "x_min", yEdge: "y_max" },
  { id: "se", xEdge: "x_max", yEdge: "y_max" },
];

const EDGE_HANDLES = [
  { id: "n", xEdge: null, yEdge: "y_min" },
  { id: "s", xEdge: null, yEdge: "y_max" },
  { id: "w", xEdge: "x_min", yEdge: null },
  { id: "e", xEdge: "x_max", yEdge: null },
];

const RESIZE_HANDLES = [...CORNER_HANDLES, ...EDGE_HANDLES];

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function boxFromCorners(startPoint, endPoint) {
  return {
    x_min: Math.min(startPoint.x, endPoint.x),
    y_min: Math.min(startPoint.y, endPoint.y),
    x_max: Math.max(startPoint.x, endPoint.x),
    y_max: Math.max(startPoint.y, endPoint.y),
  };
}

function resizeHandleCanvasPoint(handle, rectangle) {
  const x = handle.xEdge === "x_min" ? rectangle.x : handle.xEdge === "x_max" ? rectangle.x + rectangle.width : rectangle.x + rectangle.width / 2;
  const y = handle.yEdge === "y_min" ? rectangle.y : handle.yEdge === "y_max" ? rectangle.y + rectangle.height : rectangle.y + rectangle.height / 2;
  return { x, y };
}

function distanceToResizeHandle(canvasPoint, handle, rectangle) {
  if (handle.xEdge !== null && handle.yEdge !== null) {
    const handlePoint = resizeHandleCanvasPoint(handle, rectangle);
    return Math.hypot(canvasPoint.x - handlePoint.x, canvasPoint.y - handlePoint.y);
  }
  if (handle.yEdge !== null) {
    const edgeY = handle.yEdge === "y_min" ? rectangle.y : rectangle.y + rectangle.height;
    const clampedX = clamp(canvasPoint.x, rectangle.x, rectangle.x + rectangle.width);
    return Math.hypot(canvasPoint.x - clampedX, canvasPoint.y - edgeY);
  }
  const edgeX = handle.xEdge === "x_min" ? rectangle.x : rectangle.x + rectangle.width;
  const clampedY = clamp(canvasPoint.y, rectangle.y, rectangle.y + rectangle.height);
  return Math.hypot(canvasPoint.x - edgeX, canvasPoint.y - clampedY);
}

function findResizeHandle(canvasPoint, rectangle, hitRadiusCanvasPixels) {
  return (
    RESIZE_HANDLES.find((handle) => distanceToResizeHandle(canvasPoint, handle, rectangle) <= hitRadiusCanvasPixels) ?? null
  );
}

function resizeBox(originalBox, handle, photoPoint) {
  const nextXMin = handle.xEdge === "x_min" ? photoPoint.x : originalBox.x_min;
  const nextXMax = handle.xEdge === "x_max" ? photoPoint.x : originalBox.x_max;
  const nextYMin = handle.yEdge === "y_min" ? photoPoint.y : originalBox.y_min;
  const nextYMax = handle.yEdge === "y_max" ? photoPoint.y : originalBox.y_max;
  return boxFromCorners({ x: nextXMin, y: nextYMin }, { x: nextXMax, y: nextYMax });
}

function chooseDragMode({ selectedBoxIndex, resizeHandle, boxIndexAtPoint }) {
  if (selectedBoxIndex !== null && resizeHandle !== null) {
    return "resize";
  }
  return boxIndexAtPoint === -1 ? "draw" : "move";
}

if (typeof module !== "undefined") {
  module.exports = {
    RESIZE_HANDLES,
    clamp,
    boxFromCorners,
    resizeHandleCanvasPoint,
    findResizeHandle,
    resizeBox,
    chooseDragMode,
  };
}
