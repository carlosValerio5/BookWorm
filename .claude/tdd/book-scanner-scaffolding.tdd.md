# TDD Evidence: Book scanner scaffolding (cover vs ISBN)

**Source plan**: inline `/ecc:plan` output from the session on 2026-09-15 (no `.plan.md` file).
**Git checkpoints**: none. The repo was created by `uv init` during this session, and commits wait for your OK.

## User journeys
- As a thrifter, I photograph the back of a book and get its ISBN, so I can look it up.
- As a thrifter, I photograph a cover and it tells me it's a cover, with the text it read.
- As a developer, I trace any scan end to end in the logs with one `scan_id`.

## RED
Command: `uv run pytest -q --noconftest`
```
E   ModuleNotFoundError: No module named 'bookworm.annotation_drawing'
E   ModuleNotFoundError: No module named 'bookworm.barcode_reading'
E   ModuleNotFoundError: No module named 'bookworm.book_detection'
E   ModuleNotFoundError: No module named 'bookworm.cli'
E   ModuleNotFoundError: No module named 'bookworm.image_loading'
E   ModuleNotFoundError: No module named 'bookworm.isbn_validation'
E   ModuleNotFoundError: No module named 'bookworm.logging_setup'
E   ModuleNotFoundError: No module named 'bookworm.scan_classification'
9 errors in 1.25s
```
The cause is the missing implementation modules, not test setup.

## GREEN
| Command | Result |
|---|---|
| `uv run pytest -q -m "not slow"` | 58 passed, 0.41s |
| `uv run pytest -q -m slow` | 6 passed, 8.62s (real YOLO26n + EasyOCR) |
| `uv run pytest -q --cov` | 65 passed, **99% coverage** |
| `uv run bookworm annotate barcode.png out.png` | `kind: isbn`, `isbn: 9780306406157`, box drawn (checked visually) |

## Test specification
| # | Guarantee | Test | Type |
|---|---|---|---|
| 1 | ISBN-13 / ISBN-10 checksums accept valid and reject invalid, wrong length or non-digit input | `test_isbn_validation.py` | unit |
| 2 | ISBN-10 converts to the right ISBN-13 | `test_convert_isbn10_to_isbn13` | unit |
| 3 | An ISBN is pulled from free text (hyphens, spaces, lowercase x) and a bad checksum is rejected | `test_extract_isbn_from_text` | unit |
| 4 | A barcode counts as an ISBN only with the 978/979 prefix and a valid checksum | `test_is_isbn_barcode_requires_bookland_prefix_and_checksum` | unit |
| 5 | The EAN-13 barcode is decoded to an ISBN, with a box inside the image that follows the barcode's position | `test_barcode_reading.py` | integration (zxing-cpp) |
| 6 | Non-ISBN EAN barcodes and blank images return no barcodes | `test_barcode_reading.py` | integration |
| 7 | YOLO boxes turn into `BookDetection` with int boxes | `test_book_detection.py` | unit |
| 8 | The real detector has a `book` class and finds nothing on a blank image | `test_book_detection.py` (slow) | integration |
| 9 | EasyOCR output turns into `RecognizedText` | `test_text_recognition.py` | unit |
| 10 | Real OCR reads a printed ISBN that passes the checksum | `test_recognizes_isbn_printed_as_text` (slow) | integration |
| 11 | Barcode ISBN wins over text; an ISBN split across OCR lines is still found | `test_scan_classification.py` | unit |
| 12 | Kind rules: ISBN > COVER (book box) > UNKNOWN | `test_scan_classification.py` | unit |
| 13 | Full scan: barcode photo → ISBN, blank photo → UNKNOWN | `test_scan_classification.py` (slow) | integration |
| 14 | Annotation draws each box type in its color, keeps the original image unchanged, and always draws the banner | `test_annotation_drawing.py` | unit |
| 15 | Logs are JSON with call, service, level, timestamp and duration_ms; failures log a traceback and re-raise; scan_id propagates; third-party logs are JSON too | `test_logging_setup.py` | unit |
| 16 | CLI rejects a missing image (exit 2); `annotate` writes the image and prints JSON; a write failure raises | `test_cli.py` | integration |

## Known gaps
- **No real book photo tested.** COVER detection is only checked on synthetic input (a blank image gives no book). Next step: add 3–5 real photos to `tests/fixtures/` (cover close-up, cover on a shelf, a back cover with a barcode).
- `scan` command body and `main()` are uncovered (4 lines). They follow the same path as `annotate`, and `main()` ran for real in the smoke test.
- A cover that fills the whole frame may not trigger YOLO `book`, so it's classified UNKNOWN (plan risk, still open).
