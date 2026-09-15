# Plan: Book Annotator, milestone 1 (label a photo by hand)

## Context
Source: `.claude/prds/book-annotator.prd.md`, milestone 1. BookWorm has no ground truth for boxes or text on real photos. Real-photo tests only check kind and ISBN, so OCR misreads (like "Histora"), duplicate book boxes (D14) and missed sideways ISBNs are found by eye. Milestone 1 delivers a local web app. A developer opens a photo (HEIC included), classifies it first, draws typed boxes with text, saves one JSON label per photo, and can reopen and edit it. Pre-filling from the scanner (M2), the accuracy test (M3) and training export (M4) come later, but the file format has to support them now.

## Decisions
- D1 Box types, fixed list (user choice): `book`, `barcode`, `printed_isbn`, `title`, `author`, `publisher`, `other_text`.
- D2 Chandra returns layout blocks with a label, a pixel box and text, and its fine-tuning format isn't documented. We store upright boxes in original-photo pixels plus the photo's width and height, which converts to YOLO (normalized) and to Chandra-style blocks in M4. No rotated boxes.
- D3 Stack: FastAPI + uvicorn serving one static page with vanilla JS and a canvas. No build step, no CDN, no frontend framework. Lower risk than Streamlit or Gradio canvas components, which make move and edit awkward.
- D4 The server re-encodes every photo to a full-resolution JPEG via `load_image`, because browsers can't show HEIC. Browser pixels then equal the scanner's pixels, with no scale factor to get wrong.
- D5 Labels live in `labels/` (gitignored) and mirror the photo's relative path plus `.json`, e.g. `labels/cover/IMG_0012.HEIC.json`. The photo's folder name is ignored, and the class comes from the label.
- D6 Hand-drawn boxes are saved with `confirmed: true`. The flag only matters from M2 on, but it's in the format now.
- D7 The server binds to `127.0.0.1` only.

## Data structures first (`src/bookworm/annotator/annotation_types.py`)
Reuse `ScanKind` and `BoundingBox` from `src/bookworm/scan_types.py`.
```python
class BoxType(StrEnum): BOOK, BARCODE, PRINTED_ISBN, TITLE, AUTHOR, PUBLISHER, OTHER_TEXT

@dataclass(frozen=True)
class LabeledBox:            box_type: BoxType; box: BoundingBox; text: str; confirmed: bool

@dataclass(frozen=True)
class AnnotationDraft:       photo_path: str; photo_width: int; photo_height: int; kind: ScanKind
                             boxes: list[LabeledBox]; labeling_duration_ms: int     # PUT body from the browser

@dataclass(frozen=True)
class PhotoAnnotation:       schema_version: int; saved_at: str (ISO UTC, set by server) + every AnnotationDraft field
```
Saved file:
```json
{"schema_version": 1, "photo_path": "cover/IMG_0012.HEIC", "photo_width": 4284, "photo_height": 5712,
 "kind": "cover", "labeling_duration_ms": 41250, "saved_at": "2026-09-15T08:00:00Z",
 "boxes": [{"box_type": "title", "box": {"x_min": 812, "y_min": 1400, "x_max": 3300, "y_max": 1900},
            "text": "El Buscón", "confirmed": true}]}
```

## Files
New package `src/bookworm/annotator/`:
- `annotation_types.py`: the types above.
- `annotation_storage.py`, single-purpose functions:
  - `list_photo_paths(photos_dir)`: recursive, `.jpg/.jpeg/.png/.heic/.heif`, skips dotfiles, sorted.
  - `resolve_photo_path(photos_dir, photo_path)`: raises `PhotoPathError` if the path leaves `photos_dir`.
  - `annotation_path_for(labels_dir, photo_path)`
  - `save_annotation(labels_dir, annotation)`: writes atomically (temp file, then replace), UTF-8.
  - `load_annotation(annotation_path)`
  - `find_annotation_problems(draft) -> list[str]`: same pattern as `scripts/check_release_tag.py`. It catches:
    - boxes outside the photo, or with `x_min >= x_max` or `y_min >= y_max`
    - `barcode` text failing `is_isbn_barcode`, or `printed_isbn` text where `extract_isbn_from_text` finds nothing (both in `src/bookworm/isbn_validation.py`)
    - empty text on `title`, `author`, `publisher` or `other_text`
- `web_app.py`: `create_annotator_app(photos_dir, labels_dir) -> FastAPI`. Each route runs inside `log_call` from `src/bookworm/logging_setup.py`.
  - `GET /`: the page.
  - `GET /api/photos`: `[{photo_path, annotated}]`.
  - `GET /api/image?photo=`: JPEG of `load_image(...)` from `src/bookworm/image_loading.py`, via `cv2.imencode`.
  - `GET /api/annotation?photo=`: 200 with the label, or 404.
  - `PUT /api/annotation`: validates the draft. On problems, 422 with the `problems` list and nothing written. Otherwise the server stamps `saved_at` and `schema_version`, saves, and logs `annotation_saved` with kind, box count per type and `labeling_duration_ms` (the source for the PRD's time-per-photo metric).
  - A bad or missing photo returns 400 or 404, and `ImageLoadError` returns 422.
- `static/index.html`, `static/annotator.js`, `static/annotator.css`:
  - Layout: photo list on the left (with a check mark once labeled), canvas in the middle, and a right panel with class buttons plus the box list (type select, text input, delete).
  - Classify first: drawing stays disabled until a class is picked.
  - Keys: `1/2/3` pick the class (isbn/cover/unknown); `b c i t a p o` pick the box type; drag on empty space draws; drag a box moves it; `Delete` removes it; `Cmd/Ctrl+S` saves; `n` goes to the next photo.
  - Pixel conversion lives in two small pure functions (`toPhotoPixels`, `toCanvasPixels`) based on `naturalWidth / clientWidth`.
  - A timer starts when the photo loads.
- `src/bookworm/cli.py`: new command `annotator PHOTOS_DIR --labels-dir labels --port 8765`. It calls `uvicorn.run(create_annotator_app(...), host="127.0.0.1", port=port, log_config=None)` so uvicorn logs go through our JSON logger.
- `pyproject.toml`: add `fastapi` and `uvicorn` to deps and `httpx` to the dev group (needed by `TestClient`). The static files ship inside the package.
- `.gitignore`: add `labels/`.
- Docs: a line under `[Unreleased]` in `CHANGELOG.md`, a "Labeling photos" section in `README.md`, and in the PRD mark M1 `in-progress`, link this plan and close the box-types and Chandra-format open questions.

## TDD order (fast tests only, no models)
1. **Setup:** commit the PRD on `docs/annotator-prd`. Create a new worktree (branch `feat/annotator-labeling`) from it.
2. **RED:** add the tests below, run them to confirm they fail for the right reason, then commit as `test: ...`.
   - `tests/test_annotation_storage.py`:
     - photo listing (suffixes, recursion, dotfiles, order)
     - path traversal rejected (`../x`, absolute paths)
     - label path mirrors folders
     - save/load round trip with "Buscón" and no temp file left behind
     - each validation problem, plus all problems reported at once
   - `tests/test_annotator_web_app.py` (TestClient, photos from `tests/image_factories.py` including `write_heic_image`):
     - list shows the annotated flag
     - JPEG size equals the original size for both PNG and HEIC
     - 404 before saving; PUT then GET round trip
     - invalid PUT returns 422 and writes nothing
     - unknown photo and traversal attempts are rejected
   - `tests/test_cli.py`: `annotator` rejects a missing folder (exit 2) and calls `uvicorn.run` with `127.0.0.1` (monkeypatched).
3. **GREEN:** types, storage, web app, CLI and static page. Commit as `feat: ...`.
4. **Docs:** CHANGELOG, README, PRD update, `.gitignore`. Commit as `docs: ...`.

## Verification
1. `uv run pytest -m "not slow"` passes, and `uv run pytest --cov` stays at 99% or higher for `bookworm`.
2. `uv run bookworm annotator dataset/`, then use Chrome DevTools MCP on `http://127.0.0.1:8765`:
   - Open `cover/IMG_0012.HEIC`, press `2`, draw a `title` box, type "El Buscón" and save.
   - Reload the page and confirm the box comes back.
   - Check `labels/cover/IMG_0012.HEIC.json`.
   - Confirm drawing is blocked until a class is picked, and that an invalid barcode ISBN shows the 422 problems.
3. Alignment check (PRD risk): draw the saved boxes back on the full photo with `draw_labeled_box` from `src/bookworm/annotation_drawing.py` in a one-off script, then look at the image.
4. Logs: `jq 'select(.event == "annotation_saved")' logs/bookworm.jsonl` shows kind, box counts and `labeling_duration_ms`.
5. Time 5 real photos and record the median against the 1-minute target in the PRD.

Pushing and opening a PR need a separate OK after verification.
