export type Size = { width: number; height: number };

export type DetectionBox = { x_min: number; y_min: number; x_max: number; y_max: number };

export type OverlayRect = { left: number; top: number; width: number; height: number };

export function shouldCaptureFrame(lastCaptureAtMs: number, nowMs: number, intervalMs: number): boolean {
  return nowMs - lastCaptureAtMs >= intervalMs;
}

export function scaleBoxToPreview(box: DetectionBox, frameSize: Size, previewSize: Size): OverlayRect {
  const scaleX = previewSize.width / frameSize.width;
  const scaleY = previewSize.height / frameSize.height;
  return {
    left: box.x_min * scaleX,
    top: box.y_min * scaleY,
    width: (box.x_max - box.x_min) * scaleX,
    height: (box.y_max - box.y_min) * scaleY,
  };
}
