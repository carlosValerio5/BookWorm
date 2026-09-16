# TDD Evidence: labeler box resize fix

## Source plan
No `*.plan.md` was provided. Journeys were derived during this TDD run from the bug report:
"There's a bug in the labeler, the boxes can't be resized and instead of resizing a box the
cursor creates a new one, I want the user to be able to adjust and resize boxes."

## Root cause
`src/bookworm/annotator/static/annotator.js` (`startDrag`) only knew two drag modes: `draw`
(pointer outside every box) and `move` (pointer strictly inside the selected box's bounds).
There was no `resize` mode, even though the canvas already drew corner handles for the
selected box (`drawCornerHandles`). The handle squares are drawn a few pixels outside the
box's actual border, so grabbing one landed outside strict containment and fell into `draw`,
creating a new box instead of resizing the existing one.

## User journeys
1. As a user, with a box selected, I want to drag its corner handle so the box resizes instead
   of a new box being created — even when the handle sits a few pixels outside the box's border.
2. As a user, I want dragging inside a selected box (not on a handle) to still move the whole
   box, unchanged from before.
3. As a user, I want dragging in empty space to still draw a new box, unchanged from before.
4. As a user, I want a handle drag that crosses past the opposite corner to produce a valid
   (non-inverted) box instead of a corrupted one.

## Task report

- **Execution summary**: Extracted the pure hit-testing/resize math into a new
  `src/bookworm/annotator/static/box_geometry.js` (no DOM dependency, dual browser-global /
  CommonJS export), added a `resize` drag mode to `annotator.js`'s pointer lifecycle
  (`startDrag`/`continueDrag`), and wired `index.html` to load the new script first.
- **Validation commands actually run**:
  - `node --test tests/js/box_geometry.test.js`
  - `node --check src/bookworm/annotator/static/annotator.js` / `box_geometry.js`
  - `uv run pytest -q` (full suite)
  - Manual browser verification via chrome-devtools MCP against an isolated `bookworm
    annotator` instance on port 8899 with a synthetic 800×600 PNG fixture.
- **RED**: `node --test tests/js/box_geometry.test.js` failed with
  `Cannot find module '.../box_geometry.js'` (module didn't exist yet) — 1 failing, 0 passing.
- **GREEN**: same command, 10/10 passing after implementing `box_geometry.js` and wiring it in.
- **What is guaranteed by the passing tests**: the pure decision function (`chooseDragMode`)
  prioritizes a grabbed resize handle on the selected box over drawing/moving, even when the
  hit point is outside strict box containment (the exact bug scenario); `findResizeHandle`
  correctly identifies the `nw`/`se` corners and points slightly outside them within the hit
  radius, and returns `null` far from any handle; `resizeBox` moves only the dragged edge(s)
  while anchoring the opposite edge(s), and normalizes into a valid box when dragged past the
  opposite corner.
- **What the unit tests do not cover**: the DOM/canvas pointer-event wiring in `annotator.js`
  itself (`startDrag`/`continueDrag`/`resizeHandleAtPointer`) has no automated test — this repo
  has no browser/DOM test harness. This was instead verified manually (see below).

## Manual browser verification (chrome-devtools MCP)

Ran `bookworm annotator` against a synthetic fixture on an isolated port (8899 — port 8765 was
already bound by a real, already-running annotator session with the user's actual photo
library; this was caught before any interaction and is recorded as T16 in `CLAUDE.md`).
Dispatched real `PointerEvent`s on the canvas to simulate:

1. Draw a new box by dragging in empty space → 1 box created.
2. Drag the box's `se` handle → same box's `x_max`/`y_max` moved, `x_min`/`y_min` unchanged,
   box count stayed at 1 (previously this would have created a second box).
3. Drag the box's `nw` handle → `x_min`/`y_min` moved, `x_max`/`y_max` unchanged, count stayed 1.
4. Drag inside the box (not on a handle) → whole box translated by the drag offset, count
   stayed 1 (move mode unaffected).
5. Drag in empty space away from the box → a second, independent box was created; the first
   box was untouched (draw mode unaffected).

All five matched expectations; screenshot confirmed visually. Test server and browser tab were
torn down afterward.

## Test specification

| # | What is guaranteed | Test file or command | Test type | Result | Evidence |
|---|--------------------|----------------------|-----------|--------|----------|
| 1 | Grabbing a selected box's handle resizes it, even when the hit point falls outside strict box containment | `tests/js/box_geometry.test.js:findResizeHandle hits a handle slightly outside the box...` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 2 | `chooseDragMode` picks `resize` over `draw`/`move` when a handle is grabbed on the selected box | `tests/js/box_geometry.test.js:chooseDragMode resizes when a selected box's handle is grabbed...` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 3 | `chooseDragMode` still picks `draw`/`move` correctly when no handle is grabbed | `tests/js/box_geometry.test.js:chooseDragMode draws...` / `...moves the box...` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 4 | Resizing an `se`/`nw` handle moves only the dragged edges, anchoring the rest | `tests/js/box_geometry.test.js:resizeBox moves only x_max and y_max...` / `...x_min and y_min...` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 5 | Dragging a handle past the opposite corner still produces a valid (non-inverted) box | `tests/js/box_geometry.test.js:resizeBox flips into a valid box...` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 6 | End-to-end: resize/move/draw all behave correctly together on a live canvas, no cross-contamination | manual chrome-devtools MCP session against fixture on port 8899 | manual/E2E | PASS | described above, screenshot taken |
| 7 | No regression in existing Python-side annotator behavior | `uv run pytest -q` | full suite | PASS | 250 passed, 2 skipped |

## Coverage and known gaps

- `box_geometry.js` has 100% behavioral coverage of its exported functions via the 10 unit
  tests; no coverage tool was run since this is a small, newly-added, dependency-free module
  and Node's built-in runner was used without `--experimental-test-coverage` tooling wired into
  the project.
- No automated coverage for `annotator.js`'s DOM/pointer-event glue — this repo has no
  JS DOM test harness (jsdom, Playwright, etc.) and none was added, to avoid introducing new
  project tooling/dependencies for a single bug fix. This gap was closed with manual
  chrome-devtools verification instead (see above) rather than left unverified.
- Edge-midpoint resize handles (dragging just the top/bottom or left/right edge) were not
  implemented — only the four corner handles that the UI already draws. This matches the
  existing visual affordance (`drawCornerHandles`) and keeps the fix scoped to the reported bug
  rather than adding new UI surface area.

## Merge evidence

Checkpoint commits on this branch (`worktree-labeler-boxes-fix`):
- `9984092` — `test: add reproducer for labeler box resize handles` (RED)
- `20f2f2a` — `fix: resize selected box via corner handles instead of drawing a new box` (GREEN)
- `2af80ef` — `docs: changelog entry for box resize fix, record port-conflict traceback`

No refactor pass was needed beyond the initial extraction (the extraction of `clamp` and
`boxFromCorners` into the shared, testable `box_geometry.js` module happened as part of the
GREEN commit, since it was required to make the fix testable at all).
