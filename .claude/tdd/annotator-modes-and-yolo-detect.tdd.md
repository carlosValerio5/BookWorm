# TDD Evidence: labeler edit modes + YOLO "Detect books" button

**Source plan**: Inline plan from this conversation (`/ecc:plan`, conversational mode — no `*.plan.md` artifact written). The user confirmed it ("yes, use Tab for insert and Escape for normal") and asked to carry it out via `/ecc:tdd-workflow`.

## User journeys

1. As a labeler, I want an Insert edit mode where dragging always starts a new box, even on top of an existing one, so I can draw a `title`/`author`/`barcode` box nested inside a `book` box — today any click over an existing box only selects/moves/resizes it, so nested boxes can never be drawn.
2. As a labeler, I want `Tab` to toggle Normal/Insert and `Escape` to always force Normal (and cancel a box I'm mid-way through drawing), mirroring vim's modal editing so the behavior is predictable.
3. As a labeler, I want the status bar to show which mode I'm in, and auto-detected boxes to render dashed until I've reviewed them, so I don't mistake a machine guess for a confirmed label.
4. As a labeler, I want a "Detect books" button that runs the existing YOLO `book` detector on the open photo and paints each detection as a box, so I don't have to draw the outer `book` box by hand before nesting fields inside it.

## Task report

| Task | Summary | Validation command | Result |
|---|---|---|---|
| `chooseDragMode` insert-mode branch | `box_geometry.js`: `editMode === "insert"` now always returns `"draw"`, before the existing resize/move/draw logic; `editMode === "normal"` (or omitted) keeps prior behavior byte-for-byte | `node --test tests/js/box_geometry.test.js` | 19 passed (3 new, 16 pre-existing unchanged) |
| Mode state + Tab/Escape wiring | `annotator.js`: `state.editMode` (reset per photo), `startDrag` passes it into `chooseDragMode`, `Tab`→`toggleEditMode`, `Escape`→`forceNormalMode` (cancels `state.drag`, forces `"normal"`) added to the existing shortcut dispatch table | Manual browser check (no pure-function seam; DOM/event wiring) | Verified — see "Live sanity check" below |
| Status indicator + dashed unconfirmed boxes | `index.html`/`annotator.css`: `#status-edit-mode` span styled like the existing `.status-mode`; `drawLabeledBox` sets `context.setLineDash([6,4])` when `labeledBox.confirmed === false` | Manual browser check | Verified — see "Live sanity check" below |
| `GET /api/detections` | `web_app.py`: mirrors `get_photo_image`'s `find_photo_file` → `log_call` → work pattern; calls `detect_books(load_image(photo_file), load_book_detector())`, returns the `BookDetection` dataclass list directly | `uv run pytest tests/test_annotator_web_app.py -m "not slow"` then `-m slow -k detections` | 22 passed (4 new fast + 18 pre-existing), 1 passed (new real-model slow test) |
| "Detect books" button | `annotator.js`: `fetchDetections`/`detectBooks`/`detectBooksAndReportFailure` mirror `saveAnnotation`'s fetch/try-catch/`showProblems` pattern; maps each detection to `{box_type: "book", box, text: "", confirmed: false}`; gated the same way box-drawing is (`photoPath`/`kind` must be set); guards against a stale response landing after the photo was switched | Manual browser check against a real photo | Verified — see "Live sanity check" below |
| Docs | `README.md` "Labeling photos" section, `CHANGELOG.md` `[Unreleased]` (`F1` for the feature, `B4` for the nested-box bug fix) | Visual review | Done |

RED (before implementation):
```
$ node --test tests/js/box_geometry.test.js
✖ chooseDragMode draws in insert mode even when the pointer is over an existing box
  AssertionError: 'move' !== 'draw'
✖ chooseDragMode draws in insert mode even when a resize handle is grabbed
  AssertionError: 'resize' !== 'draw'

$ uv run pytest tests/test_annotator_web_app.py -k detections -m "not slow"
AttributeError: <module 'bookworm.annotator.web_app'> has no attribute 'load_book_detector'
AssertionError: assert 404 == 400   # route didn't exist yet
3 failed, 1 passed (the "missing photo -> 404" case coincidentally passed since an undefined route also 404s)
```

GREEN (after implementation):
```
$ node --test tests/js/box_geometry.test.js
ℹ tests 19
ℹ pass 19
ℹ fail 0

$ uv run pytest -m "not slow" -q
270 passed, 39 deselected, 2 warnings in 0.88s

$ uv run pytest tests/test_annotator_web_app.py -m slow -k detections -v
test_detections_endpoint_with_real_detector_finds_no_books_in_a_blank_photo PASSED
```

Live sanity check (chrome-devtools MCP against `uv run bookworm annotator dataset/ --port 8899`, real photo `cover/IMG_0012.HEIC`, per T17/T18 — explicit port, synthetic pointer events use `pointerId: 1`):
```
Opened cover/IMG_0012.HEIC (4284x5712), picked class "cover".
Clicked "Detect books" -> one dashed "book" box appeared: {x_min:639, y_min:650, x_max:3460, y_max:5028, confirmed:false},
  tightly framing the actual book in the photo.
Pressed Tab -> state.editMode became "insert" (status bar showed "INSERT" in accent color).
Dragged from inside the book box to another point inside it -> a second, solid "title" box was added:
  {x_min:1229, y_min:1229, x_max:2270, y_max:1608, confirmed:true} — fully nested inside the book box.
  This is the exact scenario that was previously impossible (B4).
Started a third drag (pointerdown+pointermove, no pointerup), then dispatched Escape ->
  state.drag became null, state.editMode became "normal", box count stayed at 2 (the in-progress drag was
  discarded, not committed as a box). Status bar showed "NORMAL" again, un-accented.
```

## Test specification

| # | What is guaranteed | Test file or command | Test type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Insert mode always draws, even when the pointer is over an existing box | `tests/js/box_geometry.test.js:chooseDragMode draws in insert mode even when the pointer is over an existing box` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 2 | Insert mode always draws, even when a resize handle is grabbed | `tests/js/box_geometry.test.js:chooseDragMode draws in insert mode even when a resize handle is grabbed` | unit | PASS | same |
| 3 | Normal mode still resizes via a grabbed handle (unchanged) | `tests/js/box_geometry.test.js:chooseDragMode still resizes in normal mode when a handle is grabbed` | unit | PASS | same |
| 4 | `/api/detections` returns the book detector's boxes as JSON, without loading the real model | `tests/test_annotator_web_app.py:test_detections_endpoint_returns_boxes_from_the_book_detector` | integration | PASS | `uv run pytest tests/test_annotator_web_app.py -m "not slow"` |
| 5 | `/api/detections` returns 404 for a photo that doesn't exist | `tests/test_annotator_web_app.py:test_detections_returns_404_for_missing_photo` | integration | PASS | same |
| 6 | `/api/detections` returns 400 for a path outside the photos folder | `tests/test_annotator_web_app.py:test_detections_rejects_path_outside_photos_folder` | integration | PASS | same |
| 7 | Calling `/api/detections` logs a `get_photo_detections` `call_finished` event | `tests/test_annotator_web_app.py:test_detections_call_is_logged` | integration | PASS | same |
| 8 | The real YOLO detector, called through the endpoint, finds no books in a blank photo | `tests/test_annotator_web_app.py:test_detections_endpoint_with_real_detector_finds_no_books_in_a_blank_photo` | integration (slow, real model) | PASS | `uv run pytest tests/test_annotator_web_app.py -m slow -k detections` |
| 9 | Existing resize/move/save/annotation-validation behavior is unaffected | full pre-existing suites | unit + integration | PASS | `uv run pytest -m "not slow" -q` → 270 passed |
| 10 | Nested box drawing, mode switching, and the Detect button work against a real photo in a real browser | manual chrome-devtools session (see above) | manual/E2E | PASS | transcript above |

## Coverage and known gaps

```
$ uv run pytest tests/test_annotator_web_app.py -m "not slow" -q --cov=bookworm.annotator.web_app --cov-report=term-missing
src/bookworm/annotator/web_app.py      86      1    99%   102
```
The one uncovered line (102) is `encode_jpeg`'s failure branch, pre-existing and unrelated to this change. The new `get_photo_detections` route is fully covered by both the fast (monkeypatched) and slow (real-model) tests.

Known, intentional gaps:
- No automated coverage tool runs against the plain-script frontend (`annotator.js`, `index.html`, `annotator.css`) — this repo doesn't have a JS coverage setup (`node --test` only, no `package.json`/nyc/c8 configured). Frontend behavior with no pure-function seam (Tab/Escape wiring, the status indicator, dashed rendering, the Detect button's fetch/render cycle) was verified manually in a real browser against a real photo instead, per the plan's own validation section.
- Clicking "Detect books" twice appends duplicate `book` boxes; not de-duplicated by design (flagged as a risk in the plan, deferred to avoid premature complexity).
- Only the YOLO `book` class is detected — `title`/`author`/`barcode`/etc. have no trained detector in this repo yet (T3), so those boxes are still drawn by hand, nested inside a detected or hand-drawn `book` box using Insert mode.

## Merge evidence

Checkpoint commits on `feature/labeler-modes-and-yolo-detect` (branched from `main`):
- `test: add reproducers for insert-mode always-draw behavior (RED)` — `2530f486`
- `fix: let insert mode always draw, enabling boxes nested inside boxes` (GREEN) — `86d5cf79`
- `feat: wire Tab/Escape edit-mode switching and dashed unconfirmed boxes` — `c05669e8`
- `test: add reproducers for /api/detections endpoint (RED)` — `0e90eae3`
- `feat: add GET /api/detections to run the YOLO book detector on a photo` (GREEN) — `90a1d76b`
- `feat: add Detect books button that paints YOLO detections as boxes` — `87e03735`
- `docs: document Normal/Insert edit modes and the Detect books button` — `ce2532d9`

No separate refactor commit was needed; both implementations matched existing repo conventions (mirroring `get_photo_image` in `web_app.py`, `setSaving`/`saveAnnotation` in `annotator.js`) on the first pass.
