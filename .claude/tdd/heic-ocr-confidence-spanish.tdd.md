# TDD Evidence: HEIC loading (B1), OCR confidence filter (D9), Spanish OCR (D10)

**Source**: findings B1, D9 and D10 from the first real photo (`dataset/cover/IMG_0012.HEIC`), 2026-09-15. No `.plan.md` file.
**Branch**: `feat/scanner-scaffolding`. RED checkpoint `c3b8149`, GREEN checkpoint `575c7af`.
**Real photos**: `dataset/` is gitignored, so real-photo tests only run on machines that have the photos.

## User journeys
- B1: an iPhone user scans a `.HEIC` photo, and it loads upright with the right colors.
- D9: scan results don't include background noise below 0.4 OCR confidence.
- D10: Spanish covers keep their accents ("Buscón").
- Every real photo in `dataset/<kind>/` is classified as its folder name.

## RED
| Item | Test | Failure |
|---|---|---|
| B1 | `test_loads_heic_image_from_disk`, `test_loads_iphone_heic_colors_in_bgr_order` | `ImageLoadError` (OpenCV can't read HEIC) |
| B1 | `test_real_photo_kind_matches_its_folder[cover/IMG_0012.HEIC]` | `ImageLoadError` |
| D9 | `test_keeps_only_text_at_or_above_minimum_confidence` | `ImportError: cannot import name 'MINIMUM_TEXT_CONFIDENCE'` |
| D10 | `test_recognizes_spanish_accents` | `assert 'ó' in 'El Busckn'` |

**D10 RED was not valid at first.** Pillow's default font draws "ó" as a box, so no reader could pass. After switching the fixture to DejaVu Sans, the check was redone by running both readers on the same image:
```
['en']       [('El Buscon', 0.6887)]   <- RED: no accent
['es', 'en'] [('EI Buscón', 0.8607)]   <- GREEN
```

## GREEN
First run: 69 passed, 3 failed. Two issues came up along the way:
- **B2 (new bug):** ultralytics replaces `PIL.Image.open`. On a missing or invalid HEIC it leaked `ModuleNotFoundError: No module named 'pi_heif'` instead of raising `ImageLoadError`. **Fix:** decode with `pillow_heif.open_heif(..., bgr_mode=True)`, which doesn't go through `Image.open`.
- **The D10 fixture font**, described above.

Final run, `uv run pytest -q --cov`: **72 passed, 1 skipped, 99% coverage.** The skip is `test_real_isbn_photo_reads_isbn_from_file_name`, because `dataset/isbn/` is empty.

Real photo through the CLI, `uv run bookworm annotate dataset/cover/IMG_0012.HEIC out.jpg`:
- `kind: cover`, loaded at 4284×5712 (portrait), scan took 2.0s
- kept texts: `Histora`, `Quevedo`, `El Buscón`
- dropped texts: `delaLiteranue`, `V H 1`

## Test specification
| # | Guarantee | Test | Type | Result |
|---|---|---|---|---|
| 1 | `.heic` and `.HEIC` files load as 3-channel images | `test_loads_heic_image_from_disk` | integration | PASS |
| 2 | HEIC colors come out in BGR order | `test_loads_iphone_heic_colors_in_bgr_order` | integration | PASS |
| 3 | Missing or invalid HEIC files raise `ImageLoadError`, never a leaked library error | `test_raises_for_missing_heic_file`, `test_raises_for_heic_file_that_is_not_an_image` | integration | PASS |
| 4 | Text below 0.4 confidence is dropped; exactly 0.4 is kept | `test_keeps_only_text_at_or_above_minimum_confidence` | unit | PASS |
| 5 | OCR keeps Spanish accents | `test_recognizes_spanish_accents` (slow) | integration | PASS |
| 6 | Each real photo's kind matches its folder | `test_real_photo_kind_matches_its_folder` (slow) | e2e | PASS (1 photo) |
| 7 | Real ISBN photos read the ISBN in their file name | `test_real_isbn_photo_reads_isbn_from_file_name` (slow) | e2e | SKIPPED (no photos) |

## Refactor
None needed. `image_loading` has one reader function per format.

## Known gaps
- **No real ISBN photo** yet, so the ISBN path is untested on a real camera photo.
- **HEIC with transparency** would load with 4 channels (BGRA). iPhone photos have no transparency. Not handled yet.
- **Full-resolution scans are slower and read worse.** At 4284×5712 the book confidence is 0.36 (0.44 at 1280px), "Historia" is read as "Histora", and "de la Literatura" falls below 0.4. Candidate fix: shrink to about 1280px on the long side before scanning.
