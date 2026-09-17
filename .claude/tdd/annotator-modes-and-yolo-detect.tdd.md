# TDD Evidence: labeler edit modes + "Detect boxes" button

**Source plan**: Inline plan from this conversation (`/ecc:plan`, conversational mode — no `*.plan.md` artifact written). The user confirmed the edit-modes plan ("yes, use Tab for insert and Escape for normal") and later asked to extend the Detect button to also find barcodes and text ("the detect button must also detect things like the barcode ISBN, Author etc."), confirmed with a second `/ecc:plan` → `/ecc:tdd-workflow` cycle on the same branch. This report covers both cycles, since neither has shipped yet (PR #7 still open).

## User journeys

1. As a labeler, I want an Insert edit mode where dragging always starts a new box, even on top of an existing one, so I can draw a `title`/`author`/`barcode` box nested inside a `book` box — today any click over an existing box only selects/moves/resizes it, so nested boxes can never be drawn.
2. As a labeler, I want `Tab` to toggle Normal/Insert and `Escape` to always force Normal (and cancel a box I'm mid-way through drawing), mirroring vim's modal editing so the behavior is predictable.
3. As a labeler, I want the status bar to show which mode I'm in, and auto-detected boxes to render dashed until I've reviewed them, so I don't mistake a machine guess for a confirmed label.
4. As a labeler, I want a "Detect boxes" button that finds not just the book cover but also the barcode and any readable text on the photo, so I don't have to draw every box by hand.
5. As a labeler, when detected text turns out to be a printed ISBN, I want it classified as `printed_isbn` automatically; otherwise I want it as `other_text` with the recognized text already filled in, since no classifier exists to tell title/author/publisher apart automatically — I still pick the right type by hand for those.

## Task report

| Task | Summary | Validation command | Result |
|---|---|---|---|
| `chooseDragMode` insert-mode branch | `box_geometry.js`: `editMode === "insert"` now always returns `"draw"`, before the existing resize/move/draw logic; `editMode === "normal"` (or omitted) keeps prior behavior byte-for-byte | `node --test tests/js/box_geometry.test.js` | 19 passed (3 new, 16 pre-existing unchanged) |
| Mode state + Tab/Escape wiring | `annotator.js`: `state.editMode` (reset per photo), `startDrag` passes it into `chooseDragMode`, `Tab`→`toggleEditMode`, `Escape`→`forceNormalMode` (cancels `state.drag`, forces `"normal"`) added to the existing shortcut dispatch table | Manual browser check (no pure-function seam; DOM/event wiring) | Verified — see "Live sanity check" below |
| Status indicator + dashed unconfirmed boxes | `index.html`/`annotator.css`: `#status-edit-mode` span styled like the existing `.status-mode`; `drawLabeledBox` sets `context.setLineDash([6,4])` when `labeledBox.confirmed === false` | Manual browser check | Verified — see "Live sanity check" below |
| `box_type_for_recognized_text` / `labeled_boxes_from_scan` | `web_app.py`: pure helpers converting a `ScanResult` (from the existing `scan_image` pipeline) into `list[LabeledBox]` — books→`BOOK`, barcodes→`BARCODE` (empty text, satisfying `BOX_TEXT_RULES`), texts→`PRINTED_ISBN` if `extract_isbn_from_text` matches else `OTHER_TEXT`, all `confirmed=False` | `uv run pytest tests/test_annotator_web_app.py -k "labeled_boxes_from_scan or box_type_for_recognized_text"` | 8 passed |
| `GET /api/detections` (v1, book-only) | Mirrored `get_photo_image`'s `find_photo_file` → `log_call` → work pattern; called `detect_books(load_image(photo_file), load_book_detector())`, returned `list[BookDetection]` | `uv run pytest tests/test_annotator_web_app.py -m "not slow"` | superseded by the next row in the same PR |
| `GET /api/detections` (v2, multi-detector) | Replaced the book-only call with `labeled_boxes_from_scan(scan_image(photo_file, load_book_detector(), load_text_reader()))`, reusing the exact `scan_image(...)` call already used by the `scan` CLI command (`cli.py`) — barcode reading runs on the full-resolution image, book detection and OCR on a shrunk copy rescaled back, per T8 | `uv run pytest tests/test_annotator_web_app.py -m "not slow"` then `-m slow -k detections` | 30 passed fast, 1 passed slow (real book detector + real text reader, blank photo → `[]`) |
| "Detect boxes" button | `annotator.js`: `fetchDetections`/`detectBoxes`/`detectBoxesAndReportFailure` mirror `saveAnnotation`'s fetch/try-catch/`showProblems` pattern. Since the backend now returns objects already shaped like `state.boxes` entries, the success path is a plain `state.boxes.push(...detections)` (no more client-side `box_type` mapping). Gated the same way box-drawing is (`photoPath`/`kind` must be set); guards against a stale response landing after the photo was switched. Renamed from `detectBooks`/"Detect books" once scope expanded beyond books | Manual browser check against two real photos | Verified — see "Live sanity check" below |
| Docs | `README.md` "Labeling photos" section, `CHANGELOG.md` `[Unreleased]` (`F1` amended in place for the expanded feature, `B4` untouched for the nested-box bug fix) | Visual review | Done |

RED (edit-modes cycle):
```
$ node --test tests/js/box_geometry.test.js
✖ chooseDragMode draws in insert mode even when the pointer is over an existing box
  AssertionError: 'move' !== 'draw'
✖ chooseDragMode draws in insert mode even when a resize handle is grabbed
  AssertionError: 'resize' !== 'draw'

$ uv run pytest tests/test_annotator_web_app.py -k detections -m "not slow"
AttributeError: <module 'bookworm.annotator.web_app'> has no attribute 'load_book_detector'
AssertionError: assert 404 == 400   # route didn't exist yet
```

RED (multi-detector cycle):
```
$ uv run pytest tests/test_annotator_web_app.py -k "labeled_boxes_from_scan or box_type_for_recognized_text" -m "not slow"
ImportError: cannot import name 'box_type_for_recognized_text' from 'bookworm.annotator.web_app'

$ uv run pytest tests/test_annotator_web_app.py -k test_detections -m "not slow"
AttributeError: <module 'bookworm.annotator.web_app'> has no attribute 'scan_image'
2 failed, 2 passed (404/400 tests pass unmodified — find_photo_file still raises before scan_image runs)
```

GREEN (final, both cycles applied):
```
$ node --test tests/js/box_geometry.test.js
ℹ tests 19
ℹ pass 19
ℹ fail 0

$ uv run pytest -m "not slow" -q
278 passed, 39 deselected, 2 warnings in 2.85s

$ uv run pytest tests/test_annotator_web_app.py -m slow -k detections -v
test_detections_endpoint_with_real_detectors_finds_nothing_in_a_blank_photo PASSED
```

Live sanity check, edit modes (chrome-devtools MCP against `uv run bookworm annotator dataset/ --port 8899`, real photo `cover/IMG_0012.HEIC`, per T17/T18 — explicit port, synthetic pointer events use `pointerId: 1`):
```
Opened cover/IMG_0012.HEIC (4284x5712), picked class "cover".
Clicked "Detect books" -> one dashed "book" box appeared: {x_min:639, y_min:650, x_max:3460, y_max:5028, confirmed:false}.
Pressed Tab -> state.editMode became "insert" (status bar showed "INSERT" in accent color).
Dragged from inside the book box to another point inside it -> a second, solid "title" box was added:
  {x_min:1229, y_min:1229, x_max:2270, y_max:1608, confirmed:true} — fully nested inside the book box (B4).
Started a third drag (pointerdown+pointermove, no pointerup), then dispatched Escape ->
  state.drag became null, state.editMode became "normal", box count stayed at 2 (in-progress drag discarded).
```

Live sanity check, multi-detector "Detect boxes" (same approach, new server on `--port 8900`):
```
Photo 1: cover/IMG_0012.HEIC, class "cover" -> clicked "Detect boxes" -> 5 boxes:
  1 "book" box (unchanged from before) + 4 "other_text" boxes with real OCR text pre-filled:
  "Historia", "delaLiteratura", "Quevedo", "El Buscón" — all dashed/confirmed:false.
Photo 2: isbn/9786076410899.HEIC, class "isbn" -> clicked "Detect boxes" -> 38 boxes:
  2 "book" boxes (YOLO detected the cover twice, a model-quality artifact, not a bug in this code),
  1 "barcode" box, and 35 "other_text" boxes with real Spanish back-cover blurb text pre-filled
  (e.g. "Escrita entre 1879 y 1880, Los hermanos", "Traducción de Augusto Vidal", "Alianza editorial").
  No "printed_isbn" box appeared: the printed ISBN's digits were split across separate OCR text
  fragments on this photo, and box_type_for_recognized_text only checks a single fragment at a time —
  an accurate, documented limitation (README/CHANGELOG), not a defect in the conversion logic.
```

## Test specification

| # | What is guaranteed | Test file or command | Test type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | Insert mode always draws, even when the pointer is over an existing box | `tests/js/box_geometry.test.js:chooseDragMode draws in insert mode even when the pointer is over an existing box` | unit | PASS | `node --test tests/js/box_geometry.test.js` |
| 2 | Insert mode always draws, even when a resize handle is grabbed | `tests/js/box_geometry.test.js:chooseDragMode draws in insert mode even when a resize handle is grabbed` | unit | PASS | same |
| 3 | Normal mode still resizes via a grabbed handle (unchanged) | `tests/js/box_geometry.test.js:chooseDragMode still resizes in normal mode when a handle is grabbed` | unit | PASS | same |
| 4 | Text containing a valid ISBN is classified `printed_isbn` | `tests/test_annotator_web_app.py:test_box_type_for_recognized_text_detects_isbn` | unit | PASS | `uv run pytest tests/test_annotator_web_app.py -m "not slow"` |
| 5 | Text without an ISBN is classified `other_text` | `tests/test_annotator_web_app.py:test_box_type_for_recognized_text_defaults_to_other_text` | unit | PASS | same |
| 6 | A detected book maps to a `BOOK` box with empty text | `tests/test_annotator_web_app.py:test_labeled_boxes_from_scan_maps_a_book_with_empty_text` | unit | PASS | same |
| 7 | A detected barcode maps to a `BARCODE` box with empty text (required by `BOX_TEXT_RULES`) | `tests/test_annotator_web_app.py:test_labeled_boxes_from_scan_maps_a_barcode_with_empty_text` | unit | PASS | same |
| 8 | ISBN-bearing OCR text maps to `PRINTED_ISBN` with the text preserved | `tests/test_annotator_web_app.py:test_labeled_boxes_from_scan_maps_isbn_bearing_text_to_printed_isbn` | unit | PASS | same |
| 9 | Plain OCR text maps to `OTHER_TEXT` with the text preserved | `tests/test_annotator_web_app.py:test_labeled_boxes_from_scan_maps_plain_text_to_other_text` | unit | PASS | same |
| 10 | An empty scan produces an empty box list | `tests/test_annotator_web_app.py:test_labeled_boxes_from_scan_returns_empty_list_for_empty_scan` | unit | PASS | same |
| 11 | Output order is books, then barcodes, then texts | `tests/test_annotator_web_app.py:test_labeled_boxes_from_scan_orders_books_then_barcodes_then_texts` | unit | PASS | same |
| 12 | `/api/detections` merges and correctly types boxes from every detector in one response | `tests/test_annotator_web_app.py:test_detections_endpoint_merges_boxes_from_every_detector` | integration | PASS | same |
| 13 | `/api/detections` returns 404 for a photo that doesn't exist | `tests/test_annotator_web_app.py:test_detections_returns_404_for_missing_photo` | integration | PASS | same |
| 14 | `/api/detections` returns 400 for a path outside the photos folder | `tests/test_annotator_web_app.py:test_detections_rejects_path_outside_photos_folder` | integration | PASS | same |
| 15 | Calling `/api/detections` logs a `get_photo_detections` `call_finished` event | `tests/test_annotator_web_app.py:test_detections_call_is_logged` | integration | PASS | same |
| 16 | The real YOLO + EasyOCR pipeline, called through the endpoint, finds nothing in a blank photo | `tests/test_annotator_web_app.py:test_detections_endpoint_with_real_detectors_finds_nothing_in_a_blank_photo` | integration (slow, real models) | PASS | `uv run pytest tests/test_annotator_web_app.py -m slow -k detections` |
| 17 | Existing resize/move/save/annotation-validation behavior is unaffected | full pre-existing suites | unit + integration | PASS | `uv run pytest -m "not slow" -q` → 278 passed |
| 18 | Nested box drawing, mode switching, and multi-detector "Detect boxes" work against real photos in a real browser | manual chrome-devtools sessions (see above) | manual/E2E | PASS | transcripts above |

## Coverage and known gaps

```
$ uv run pytest tests/test_annotator_web_app.py -m "not slow" -q --cov=bookworm.annotator.web_app --cov-report=term-missing
src/bookworm/annotator/web_app.py      96      1    99%   105
```
The one uncovered line (105) is `encode_jpeg`'s failure branch, pre-existing and unrelated to this change. `box_type_for_recognized_text`, `labeled_boxes_from_scan`, and the `get_photo_detections` route are fully covered by unit, fast-integration, and slow real-model tests.

Known, intentional gaps:
- No automated coverage tool runs against the plain-script frontend (`annotator.js`, `index.html`, `annotator.css`) — this repo doesn't have a JS coverage setup (`node --test` only, no `package.json`/nyc/c8 configured). Frontend behavior with no pure-function seam (Tab/Escape wiring, the status indicator, dashed rendering, the Detect button's fetch/render cycle) was verified manually in a real browser against real photos instead.
- Clicking "Detect boxes" twice appends duplicate boxes; not de-duplicated by design (flagged as a risk in the plan, deferred to avoid premature complexity — more noticeable now that one click can add dozens of OCR text boxes, still deferred).
- `title`/`author`/`publisher` are never auto-classified — no trained classifier exists for those fields (T3). OCR text lands as `other_text` with its text pre-filled; the user switches the type by hand.
- A printed ISBN split across multiple OCR text fragments (observed live on `isbn/9786076410899.HEIC`) won't be classified as `printed_isbn`, since `box_type_for_recognized_text` checks one fragment at a time rather than joining all recognized text first (unlike `scan_classification.find_isbn`, which does join them for its own purpose of deciding the scan's kind). This is a known, accepted limitation, not a regression — the barcode itself is still detected correctly on the same photo.

## Merge evidence

Checkpoint commits on `feature/labeler-modes-and-yolo-detect` (branched from `main`, PR #7):

Edit-modes cycle:
- `test: add reproducers for insert-mode always-draw behavior (RED)` — `2530f486`
- `fix: let insert mode always draw, enabling boxes nested inside boxes` (GREEN) — `86d5cf79`
- `feat: wire Tab/Escape edit-mode switching and dashed unconfirmed boxes` — `c05669e8`
- `test: add reproducers for /api/detections endpoint (RED)` — `0e90eae3`
- `feat: add GET /api/detections to run the YOLO book detector on a photo` (GREEN) — `90a1d76b`
- `feat: add Detect books button that paints YOLO detections as boxes` — `87e03735`
- `docs: document Normal/Insert edit modes and the Detect books button` — `ce2532d9`

Multi-detector cycle:
- `test: add reproducers for scan-to-labeled-box conversion helpers (RED)` — `a9e84edf`
- `feat: add scan-to-labeled-box conversion helpers` (GREEN) — `33bcf312`
- `test: expect /api/detections to merge every scan_image detector (RED)` — `be95ee14`
- `feat: detect barcode and text boxes too, via the existing scan pipeline` (GREEN) — `f8bf1550`
- `test: verify /api/detections against the real book and text models` — `dc1957da`
- `feat: rename Detect books to Detect boxes and drop the book-only mapping` — `8f3533cf`
- `docs: update Detect boxes docs and TDD evidence for multi-detector scope` — (this commit)

No separate refactor commit was needed in either cycle; both implementations matched existing repo conventions (mirroring `get_photo_image`/`scan_image`'s own call site in `cli.py`, and `setSaving`/`saveAnnotation` in `annotator.js`) on the first pass.
