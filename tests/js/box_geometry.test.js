const test = require("node:test");
const assert = require("node:assert/strict");
const {
  findResizeHandle,
  resizeBox,
  chooseDragMode,
} = require("../../src/bookworm/annotator/static/box_geometry.js");

const RECTANGLE = { x: 100, y: 100, width: 50, height: 40 };
const HIT_RADIUS = 6;
const BOX = { x_min: 200, y_min: 200, x_max: 300, y_max: 260 };

test("findResizeHandle hits the bottom-right corner handle", () => {
  const handle = findResizeHandle({ x: 150, y: 140 }, RECTANGLE, HIT_RADIUS);
  assert.equal(handle.id, "se");
});

test("findResizeHandle hits the top-left corner handle", () => {
  const handle = findResizeHandle({ x: 100, y: 100 }, RECTANGLE, HIT_RADIUS);
  assert.equal(handle.id, "nw");
});

test("findResizeHandle hits a handle slightly outside the box, where the drawn handle square extends", () => {
  const handle = findResizeHandle({ x: 154, y: 144 }, RECTANGLE, HIT_RADIUS);
  assert.equal(handle.id, "se");
});

test("findResizeHandle returns null far away from every handle", () => {
  const handle = findResizeHandle({ x: 125, y: 120 }, RECTANGLE, HIT_RADIUS);
  assert.equal(handle, null);
});

test("chooseDragMode resizes when a selected box's handle is grabbed, even outside strict containment", () => {
  const mode = chooseDragMode({ selectedBoxIndex: 0, resizeHandle: { id: "se" }, boxIndexAtPoint: -1 });
  assert.equal(mode, "resize");
});

test("chooseDragMode draws a new box when nothing is selected and no box is under the pointer", () => {
  const mode = chooseDragMode({ selectedBoxIndex: null, resizeHandle: null, boxIndexAtPoint: -1 });
  assert.equal(mode, "draw");
});

test("chooseDragMode moves the box under the pointer when no handle is grabbed", () => {
  const mode = chooseDragMode({ selectedBoxIndex: 0, resizeHandle: null, boxIndexAtPoint: 0 });
  assert.equal(mode, "move");
});

test("resizeBox moves only x_max and y_max for the se handle, keeping x_min and y_min anchored", () => {
  const resized = resizeBox(BOX, { id: "se", xEdge: "x_max", yEdge: "y_max" }, { x: 320, y: 280 });
  assert.deepEqual(resized, { x_min: 200, y_min: 200, x_max: 320, y_max: 280 });
});

test("resizeBox moves only x_min and y_min for the nw handle, keeping x_max and y_max anchored", () => {
  const resized = resizeBox(BOX, { id: "nw", xEdge: "x_min", yEdge: "y_min" }, { x: 180, y: 190 });
  assert.deepEqual(resized, { x_min: 180, y_min: 190, x_max: 300, y_max: 260 });
});

test("resizeBox flips into a valid box when the handle is dragged past the opposite corner", () => {
  const resized = resizeBox(BOX, { id: "se", xEdge: "x_max", yEdge: "y_max" }, { x: 150, y: 150 });
  assert.deepEqual(resized, { x_min: 150, y_min: 150, x_max: 200, y_max: 200 });
});
