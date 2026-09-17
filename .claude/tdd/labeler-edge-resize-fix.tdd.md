# TDD Evidence: labeler edge resize fix

## Source plan
No `*.plan.md` was provided. Journeys were derived during this TDD run from the bug report:
"It's not working, it only moves the box but it doesn't resize it" — reported right after the
prior corner-handle resize fix (`20f2f2a6`) landed.

## Root cause
`src/bookworm/annotator/static/box_geometry.js`'s `RESIZE_HANDLES` only defined the four
**corner** handles (`nw`/`ne`/`sw`/`se`), each hit-tested as a 6-canvas-pixel-radius circle
around a single point. Grabbing anywhere along a selected box's **edge** — not precisely one of
the four small corner squares — misses every handle, so `findResizeHandle` returns `null`,
`chooseDragMode` falls through to `"move"`, and the whole box translates instead of resizing.
This is a real, easy-to-hit UX gap: a user's natural instinct is to grab the border of a
selected box anywhere along its length, not to land within a few pixels of a corner. This gap
was already called out as a known limitation in the prior fix's TDD evidence
(`.claude/tdd/labeler-boxes-fix.tdd.md`, "Coverage and known gaps").

Reproduced live (not just inferred) via chrome-devtools MCP against an isolated `bookworm
annotator` instance on a synthetic 4032×3024 fixture (matching real phone-photo scale, where
the small corner-hit-radius is easy to miss): dragging the exact midpoint of a selected box's
right edge moved the box's `x_min`/`y_min` and left its width/height unchanged — a move, not a
resize.

## User journeys
1. As a user, with a box selected, I want to drag anywhere along one of its edges — not just a
   tiny corner square — and have that edge resize, not the whole box move.
2. As a user, I want grabbing a corner to still take priority over an edge when both are close
   (e.g. right at the corner itself), unchanged from the prior fix.
3. As a user, I want dragging inside a selected box, away from any edge or corner, to still move
   the whole box, unchanged from before.
4. As a user, I want dragging in empty space to still draw a new box, unchanged from before.

## Task report

- **Execution summary**: Split `RESIZE_HANDLES` into `CORNER_HANDLES` (point hit-test, radius)
  and `EDGE_HANDLES` (`n`/`s`/`e`/`w`, band hit-test — perpendicular distance to the edge line,
  clamped along its length), combined with corners first so a corner wins ties. Generalized
  `resizeHandleCanvasPoint` to place edge handles at each edge's midpoint (for drawing) and added
  `distanceToResizeHandle` to compute the right kind of distance per handle. `resizeBox` and
  `chooseDragMode` needed no changes — both already handled a handle with only one of
  `xEdge`/`yEdge` set correctly. Renamed `annotator.js`'s `drawCornerHandles` to
  `drawResizeHandles`, now drawing all 8 handle squares (corners + edge midpoints) by iterating
  `RESIZE_HANDLES` instead of a hardcoded 4-corner array.
- **Validation commands actually run**:
  - `node --test tests/js/box_geometry.test.js`
  - `node --check src/bookworm/annotator/static/annotator.js` / `box_geometry.js`
  - `uv run pytest -q` (full suite)
  - Manual browser verification via chrome-devtools MCP against an isolated `bookworm
    annotator` instance on port 8899 with a synthetic 4032×3024 JPEG fixture (real phone-photo
    scale, ~5x display downscale).
- **RED**: `node --test tests/js/box_geometry.test.js` — 3 of 6 new tests failed (2 with `null`
  handle for an edge-midpoint/edge-quarter-point grab, 1 matched the wrong corner for a
  too-close test point which was then corrected) — 13 passing, 3 failing.
- **GREEN**: same command, 16/16 passing after implementing edge handles in `box_geometry.js`.
- **What is guaranteed by the passing tests**: `findResizeHandle` recognizes a grab anywhere
  along an edge's length (midpoint and off-midpoint points alike), not just its two endpoints;
  a corner still wins when a point is close to both a corner and an adjacent edge; points in the
  open interior still return `null`. `resizeBox` for an edge handle (only `xEdge` or only
  `yEdge` set) moves just that one edge, anchoring the other three.
- **What the unit tests do not cover**: the DOM/canvas pointer-event wiring in `annotator.js`
  (unchanged in this fix beyond the `drawResizeHandles` rename/generalization) — same gap as the
  prior fix, closed the same way, with manual verification below.

## Manual browser verification (chrome-devtools MCP)

Ran `bookworm annotator` against a synthetic 4032×3024 fixture on an isolated port (8899, same
port used by the prior fix's verification — confirmed free and confirmed the serving instance
matched the fixture's single photo before interacting, per T17). Dispatched real `PointerEvent`s
on the canvas, using `pointerId: 1` throughout (see T18 — other synthetic pointer IDs make
`setPointerCapture` throw and silently no-op the drag, which cost significant time to track down
during this session and produced several false "still broken" / false "already works" readings
before the cause was found).

Before the fix:
1. Drew a box, selected it (auto-selected on draw).
2. Dragged the exact midpoint of its right edge → the box **moved** (`x_min`/`y_min` shifted by
   the drag offset, width/height unchanged) instead of resizing. This reproduced the reported
   bug exactly.

After the fix:
1. Same drag (right-edge midpoint) → `x_min`/`y_min` stayed anchored, only the box's width grew
   by the drag offset — a correct resize.
2. Interior drag (away from every handle) → whole box translated, size unchanged — move mode
   still works, no regression.
3. Screenshot of a selected box confirmed all 8 handle squares (4 corners + 4 edge midpoints)
   render correctly.
4. Checked the browser console: no new errors from application code (one pre-existing, expected
   404 for `GET /api/annotation` on a not-yet-labeled photo, matching
   `test_annotation_is_404_before_saving`).

Test server and browser tab were torn down afterward.

## Test specification

| # | What is guaranteed | Test file or command | Test type | Result | Evidence |
|---|--------------------|----------------------|-----------|--------|----------|
| 1 | Grabbing a selected box's edge anywhere along its length (not just a corner) is recognized as a resize handle | `tests/js/box_geometry.test.js:findResizeHandle hits the right edge at its midpoint...` / `...a quarter of the way along it...` / `...the top edge anywhere along its length` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 2 | A corner still wins over an adjacent edge when a grab point is close to both | `tests/js/box_geometry.test.js:findResizeHandle still prefers the corner over the edge...` | unit | PASS | same |
| 3 | Existing corner-handle and interior/empty-space behavior is unchanged | `tests/js/box_geometry.test.js:findResizeHandle hits the bottom-right corner handle` / `...top-left...` / `...slightly outside the box...` / `...returns null far away...` / `chooseDragMode ...` (all pre-existing) | unit | PASS | same |
| 4 | `resizeBox` for an edge handle moves only that edge, anchoring the rest | `tests/js/box_geometry.test.js:resizeBox moves only x_max for the e (right edge) handle...` / `...only y_min for the n (top edge) handle...` | unit | PASS | same |
| 5 | End-to-end: an edge grab resizes (not moves) on a live canvas at real phone-photo scale; move and draw modes unaffected | manual chrome-devtools MCP session against a 4032×3024 fixture on port 8899 | manual/E2E | PASS | described above, screenshot taken |
| 6 | No regression in existing Python-side annotator behavior | `uv run pytest -q` | full suite | PASS | 275 passed, 2 skipped |

## Coverage and known gaps

- `box_geometry.js` has behavioral coverage of the new edge-handle paths (16/16 unit tests); no
  coverage tool was run, consistent with the prior fix's approach for this small,
  dependency-free module.
- No automated coverage for `annotator.js`'s DOM/pointer-event glue or the `drawResizeHandles`
  rendering change — same pre-existing gap as the prior fix, closed with manual chrome-devtools
  verification instead.
- Edge hit-testing uses the same 6-canvas-pixel band width as the corner hit-radius; this was not
  separately tuned. If real-world use still finds edges hard to grab, widening that constant
  (`RESIZE_HANDLE_HIT_RADIUS_CANVAS_PIXELS` in `annotator.js`) is the first thing to try before
  changing the hit-testing logic itself.

## Merge evidence

Checkpoint commits on this branch (`fix/labeler-resize-handle-bug`, worktree
`.claude/worktrees/labeler-resize-handle-fix`):
- test: add reproducers for edge-handle resize (RED)
- fix: recognize edge grabs, not just corners, as resize handles (GREEN)
- docs: changelog entry and tracebacks for the edge-resize fix and the pointer-capture testing
  gotcha

No refactor pass was needed beyond the initial split of `RESIZE_HANDLES` into
`CORNER_HANDLES`/`EDGE_HANDLES`, which happened as part of the GREEN commit since it was needed
to make the fix testable in the first place.
