# TDD Evidence: Scan a 1280px copy (D11) + real ISBN photo test

**Source**: finding D11 (full-resolution scans are slow and read worse) and your new ISBN photo `dataset/isbn/9786076410899.HEIC`, 2026-09-15. No `.plan.md` file.
**Branch**: `feat/scanner-scaffolding`. RED checkpoint `3dbc6b7`, GREEN checkpoint `d4141fa`.

## User journeys
- As a thrifter, a scan comes back fast, and cover text reads at least as well as before.
- As a thrifter, a small barcode on a big phone photo still gives me the ISBN.
- As a developer, every box is in the original photo's coordinates, so annotations and later crops line up.

## Probe before writing tests
Real photos at 4284×5712, full resolution vs a 1280px copy:
```
isbn  full  barcode ['9786076410899']  ocr 5183ms
isbn  1280  barcode []                 ocr 1357ms   <- barcode lost
cover full  barcode []                 ocr 1953ms
cover 1280  barcode []                 ocr  432ms
```
**Design, based on the probe:** barcodes are read on the full-resolution image; YOLO and OCR run on the 1280px copy; boxes are scaled back up.

## RED (`uv run pytest --continue-on-collection-errors`)
```
E   ImportError: cannot import name 'shrink_image_to_long_side' from 'bookworm.image_loading'
E   ImportError: cannot import name 'scale_boxes_to_original' from 'bookworm.scan_classification'
E   AttributeError: 'BoundingBox' object has no attribute 'scaled'
1 failed, 59 passed, 2 errors
```

**Guard tests.** These already pass on the old code and would only fail after a wrong D11 change:
- `test_scan_reads_small_barcode_in_large_photo` fails if barcodes are read on the shrunk copy.
- `test_scan_reports_text_boxes_in_original_photo_coordinates` fails if boxes aren't scaled back.
- `test_real_isbn_photo_reads_isbn_from_file_name` passed at baseline (3 passed at full resolution). It has no RED of its own.

## GREEN
`uv run pytest -q --cov`: **82 passed, 0 skipped, 99% coverage.**

Real photos, `uv run bookworm annotate`:

| Photo | Before | After |
|---|---|---|
| `isbn/9786076410899` | OCR alone 5.2s | scan **1.7s**, `kind: isbn`, `isbn: 9786076410899` |
| `cover/IMG_0012` | scan 2.0s, book 0.36, "Histora", "de la Literatura" dropped | scan **0.9s**, book 0.41, "Historia", "delaLiteratura" kept |

The annotated ISBN photo was checked visually: the barcode and text boxes line up at full resolution.

## Test specification
| # | Guarantee | Test | Type | Result |
|---|---|---|---|---|
| 1 | Large images shrink to a 1280px long side (landscape and portrait) | `test_shrinks_large_image_to_long_side` | unit | PASS |
| 2 | The shrunk image remembers the factor back to the original | `test_shrunk_image_remembers_scale_back_to_original` | unit | PASS |
| 3 | Small images keep their size (no upscaling) | `test_keeps_small_image_at_original_size` | unit | PASS |
| 4 | `BoundingBox.scaled` multiplies every coordinate | `test_bounding_box_scaled_multiplies_every_coordinate` | unit | PASS |
| 5 | Scaling boxes keeps confidence and the other fields | `test_scale_boxes_to_original_scales_box_and_keeps_other_fields` | unit | PASS |
| 6 | A small barcode in a 4000×3000 photo is still read | `test_scan_reads_small_barcode_in_large_photo` (slow) | integration | PASS |
| 7 | Text boxes are reported in original photo coordinates | `test_scan_reports_text_boxes_in_original_photo_coordinates` (slow) | integration | PASS |
| 8 | A real ISBN photo scans as `isbn` with the ISBN in its file name | `test_real_isbn_photo_reads_isbn_from_file_name`, `test_real_photo_kind_matches_its_folder` (slow) | e2e | PASS |

## Refactor
None needed.

## Known gaps
- **D14:** YOLO returns overlapping book boxes (0.47 and 0.27 on the ISBN photo). It doesn't change the kind, but the boxes are noisy.
- **D15:** annotation line width and font size are fixed, so they're too small to read on full-resolution photos.
- The sideways printed "ISBN 978-607-641-089-9" is split into separate OCR pieces, so an ISBN printed without a barcode, sideways, would be missed. The barcode covers this photo.
- The real-photo tests cover only 2 photos.
