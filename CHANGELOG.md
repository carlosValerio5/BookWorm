# Changelog

All notable changes to BookWorm are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every release has a git tag named `vMAJOR.MINOR.PATCH` that matches the version in `pyproject.toml` and a dated section below. See [Releasing](README.md#releasing).

## [Unreleased]

### Added
- `bookworm-crawl run <source>` collects candidate photos for YOLO fine-tuning. A run picks up where the last one stopped, obeys robots.txt, waits between requests to each site, and stops on 429. State is kept in `dataset/crawled/crawl_state.sqlite3`.
- `bookworm-crawl status` prints request counts per source and saved photos per hint label.
- `blog_pages` source: approved book-haul blogs from `crawler_seeds/blog_pages.toml`, photos from 600px.
- `commons_categories` source: Wikimedia Commons category pages from `crawler_seeds/commons_categories.toml`. Downloads the largest standard thumbnail of at least 640px, keeps the license, and skips PNGs.
- `openverse_photos` source. It collects nothing today, because Openverse's robots.txt blocks its image API (D17).
- Every saved photo carries a hint label (`cover`, `isbn` or `spine`) and where it came from.
- Crawler safety limits: a 401 or 403 fails that one request instead of stopping the run; redirects are queued as new requests, so the target's robots.txt is checked and the photo is saved under its final URL; responses stop at 30 MB; image size is read from the file header, and images over 16384px are skipped; hosts that resolve to loopback, private or link-local addresses are skipped.
- `bookworm annotator PHOTOS_DIR` opens a local web app at `http://127.0.0.1:8765` for labeling book photos by hand. You pick the class first, then draw boxes typed as `book`, `barcode`, `printed_isbn`, `title`, `author`, `publisher` or `other_text` and type the text inside each text box. Barcode boxes have no text. Every photo gets one JSON label in `labels/` with boxes in the original photo's pixels (Book Annotator PRD, milestone 1).
- `bookworm fetch-drive FOLDER_URL` downloads every photo from a public ("anyone with the link") Google Drive folder into `dataset/drive/` (or `--output-dir`), flat and ready for `bookworm annotator`. Rerunning it skips files already downloaded.

### Changed
- Terminal logs are readable `event key=value` lines, colored in a real terminal. `logs/bookworm.jsonl` still gets every event as JSON.
- The annotator is redesigned in the style of Cursor's website: a warm dark window with the photo path in the title bar, a larger photo, photos grouped into "To label" and "Labeled" with box counts, a status bar with mode, box type, cursor pixels and a labeling timer, and box tags that avoid covering other boxes. Keyboard shortcuts and the class-first lock are unchanged.
- `/api/photos` returns each photo's `box_count`.

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
