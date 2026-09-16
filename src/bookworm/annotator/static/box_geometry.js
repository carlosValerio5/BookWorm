const RESIZE_HANDLES = [
  { id: "nw", xEdge: "x_min", yEdge: "y_min" },
  { id: "ne", xEdge: "x_max", yEdge: "y_min" },
  { id: "sw", xEdge: "x_min", yEdge: "y_max" },
  { id: "se", xEdge: "x_max", yEdge: "y_max" },
];

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
  return {
    x: handle.xEdge === "x_min" ? rectangle.x : rectangle.x + rectangle.width,
    y: handle.yEdge === "y_min" ? rectangle.y : rectangle.y + rectangle.height,
  };
}

function findResizeHandle(canvasPoint, rectangle, hitRadiusCanvasPixels) {
  return (
    RESIZE_HANDLES.find((handle) => {
      const handlePoint = resizeHandleCanvasPoint(handle, rectangle);
      return Math.hypot(canvasPoint.x - handlePoint.x, canvasPoint.y - handlePoint.y) <= hitRadiusCanvasPixels;
    }) ?? null
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
