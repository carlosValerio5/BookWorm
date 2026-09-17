# Changelog

All notable changes to BookWorm are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every release has a git tag named `vMAJOR.MINOR.PATCH` that matches the version in `pyproject.toml` and a dated section below. See [Releasing](README.md#releasing).

## [Unreleased]

### Added
- Mobile product and design docs (`bookworm-mobile/PRODUCT.md`, `bookworm-mobile/DESIGN.md`): warm dark "Viewfinder" north star, screen map, and shared tokens in `bookworm-mobile/src/constants/theme.ts`.
- Mobile UI: warm dark scan and biblioteca screens with vintage gold (`#f2cc8f`) star accents, gold-framed camera, and token-driven styling.
- `bookworm-crawl run <source>` collects candidate photos for YOLO fine-tuning. A run picks up where the last one stopped, obeys robots.txt, waits between requests to each site, and stops on 429. State is kept in `dataset/crawled/crawl_state.sqlite3`.
- `bookworm-crawl status` prints request counts per source and saved photos per hint label.
- `blog_pages` source: approved book-haul blogs from `crawler_seeds/blog_pages.toml`, photos from 600px.
- `commons_categories` source: Wikimedia Commons category pages from `crawler_seeds/commons_categories.toml`. Downloads the largest standard thumbnail of at least 640px, keeps the license, and skips PNGs.
- `openverse_photos` source. It collects nothing today, because Openverse's robots.txt blocks its image API (D17).
- Every saved photo carries a hint label (`cover`, `isbn` or `spine`) and where it came from.
- Crawler safety limits: a 401 or 403 fails that one request instead of stopping the run; redirects are queued as new requests, so the target's robots.txt is checked and the photo is saved under its final URL; responses stop at 30 MB; image size is read from the file header, and images over 16384px are skipped; hosts that resolve to loopback, private or link-local addresses are skipped.
- `bookworm annotator PHOTOS_DIR` opens a local web app at `http://127.0.0.1:8765` for labeling book photos by hand. You pick the class first, then draw boxes typed as `book`, `barcode`, `printed_isbn`, `title`, `author`, `publisher` or `other_text` and type the text inside each text box. Barcode boxes have no text. Every photo gets one JSON label in `labels/` with boxes in the original photo's pixels (Book Annotator PRD, milestone 1).
- `bookworm fetch-drive FOLDER_URL` downloads every photo from a public ("anyone with the link") Google Drive folder into `dataset/drive/` (or `--output-dir`), flat and ready for `bookworm annotator`. Rerunning it skips files already downloaded. A file whose name collides with a different Drive file's name (two distinct files sharing the same iPhone-style filename, for example) is saved with its Drive file ID prefixed, so a collision never silently drops a photo (B2).
- `bookworm build-yolo-dataset PHOTOS_DIR` converts labeled photos (from `bookworm annotator`) into a YOLO training dataset at `dataset/yolo/` (`images/{train,val}`, `labels/{train,val}`, `data.yaml`), with the 7 annotator box classes (`book`, `barcode`, `printed_isbn`, `title`, `author`, `publisher`, `other_text`) as YOLO class ids 0-6. The train/val split is deterministic per photo, so labeling more photos later doesn't reshuffle ones already placed. Unlabeled photos are skipped, not errored.
- `bookworm train-yolo DATASET_YAML` fine-tunes the existing `models/yolo26n.pt` weights on a dataset built by `build-yolo-dataset` and prints the path to the resulting best checkpoint.
- Annotator edit modes: `Tab` toggles Normal and Insert, `Escape` cancels any in-progress drag and forces Normal. In Insert mode, dragging always starts a new box, even on top of an existing one, so boxes can be nested (a `title` box inside a `book` box, for example) (F1).
- Annotator "Detect boxes" button: calls `GET /api/detections`, which runs the existing `scan_image` pipeline (YOLO `book` detection, zxing barcode reading, and EasyOCR text recognition) on the open photo. Adds a `book` box per detected cover, a `barcode` box per barcode, a `printed_isbn` box for any recognized text that contains a valid ISBN, and an `other_text` box (pre-filled with the recognized text) for everything else — all unconfirmed and drawn dashed until reviewed. `title`/`author`/`publisher` still aren't auto-classified (no trained classifier exists for those fields), so an `other_text` box still needs its type switched by hand (F1).

### Changed
- Terminal logs are readable `event key=value` lines, colored in a real terminal. `logs/bookworm.jsonl` still gets every event as JSON.
- The annotator is redesigned in the style of Cursor's website: a warm dark window with the photo path in the title bar, a larger photo, photos grouped into "To label" and "Labeled" with box counts, a status bar with mode, box type, cursor pixels and a labeling timer, and box tags that avoid covering other boxes. Keyboard shortcuts and the class-first lock are unchanged.
- `/api/photos` returns each photo's `box_count`.

### Fixed
- Dragging a selected box's corner handle now resizes that box instead of drawing a new one on top of it (B2).
- Dragging a selected box's edge — not just one of its four corners — now resizes that edge instead of moving the whole box (B3).
- A box could never be drawn inside or on top of an existing box, so nested regions (a `title` box inside a `book` box) couldn't be labeled at all. Fixed by the new Insert edit mode (B4).

## [0.1.0] - 2026-09-15

### Added
- `bookworm scan` prints a JSON result that says whether a photo shows an ISBN, a cover, or neither (`kind`: `isbn`, `cover`, `unknown`).
- `bookworm annotate` also saves a copy of the photo with boxes drawn around books, barcodes and text.
- ISBNs are read from EAN-13 barcodes with zxing-cpp. A barcode only counts if it starts with 978 or 979 and its checksum is valid.
- ISBN-10 and ISBN-13 numbers printed as text are found in the OCR output, even when OCR splits them over two lines.
- Book detection with YOLO26n, using the COCO `book` class.
- Text recognition with EasyOCR in Spanish and English, so accents like "Buscón" survive (D10).
- Text below 0.4 OCR confidence is dropped (D9).
- HEIC photos from iPhones load upright with the right colors (B1).
- YOLO and OCR run on a copy shrunk to 1280px on the long side, while barcodes are still read at full resolution. Boxes are reported in the original photo's coordinates (D11).
- JSON logs to stderr and `logs/bookworm.jsonl`. Every line has a timestamp, level, service, call and duration, and all lines from one photo share a `scan_id`.
- README with a banner, a demo scan and a pipeline diagram.
- This changelog, and a CI check that rejects release tags that aren't `vMAJOR.MINOR.PATCH` or don't match `pyproject.toml` and this file.

[Unreleased]: https://github.com/carlosValerio5/BookWorm/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/carlosValerio5/BookWorm/releases/tag/v0.1.0
