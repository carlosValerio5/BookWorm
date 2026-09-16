# TDD Evidence: bookworm fetch-drive

**Source plan**: Inline plan from this conversation (no `*.plan.md` artifact was written; conversational mode). Confirmed by the user invoking `/ecc:tdd-workflow` immediately after the plan was presented.

## User journeys

1. As a user, I want to run `bookworm fetch-drive <folder_url>` so that photos from a public Google Drive folder are downloaded into a directory I can hand to `bookworm annotator`.
2. As a user, when I rerun `fetch-drive` after adding more photos to Drive, I want only new files downloaded, so reruns are cheap.
3. As a user, if the download fails (bad folder URL, a file fails partway), I want a clear error and a non-zero exit, not a silent empty result.

## Task report

| Task | Summary | Validation command | Result |
|---|---|---|---|
| `download_drive_folder` | Thin, logged wrapper over `gdown.download_folder(url=, output=, quiet=False, use_cookies=False, resume=True)`. `output` is passed without a trailing separator so gdown treats the given directory as the download root instead of nesting a subfolder named after the Drive folder. Wraps `gdown.exceptions.DownloadError` in `DriveDownloadError`. | `uv run pytest tests/test_drive_download.py -q` | 3 passed |
| `bookworm fetch-drive` CLI command | New Typer command in `src/bookworm/cli.py`, default `--output-dir dataset/drive`, prints `{"downloaded": N, "output_dir": "..."}`, exits 1 on `DriveDownloadError`. | `uv run pytest tests/test_cli.py -q` | 8 passed (3 new `fetch-drive` tests + 5 pre-existing) |

RED (before implementation):
```
$ uv run pytest tests/test_drive_download.py tests/test_cli.py -q
ModuleNotFoundError: No module named 'bookworm.drive_download'
2 errors in 0.65s
```

GREEN (after implementation):
```
$ uv run pytest tests/test_drive_download.py tests/test_cli.py -q
...........                                                              [100%]
11 passed in 2.82s
```

Full regression check:
```
$ uv run pytest -q -m "not slow"
247 passed, 12 deselected, 2 warnings in 1.15s
```

## Test specification

| # | What is guaranteed | Test file or command | Test type | Result | Evidence |
|---|---|---|---|---|---|
| 1 | `download_drive_folder` calls gdown with the folder URL, resume=True, and an output path with no trailing separator (so files land flat, not nested under an extra Drive-folder-name directory) | `tests/test_drive_download.py:test_download_drive_folder_calls_gdown_with_flat_output_and_resume` | unit | PASS | `uv run pytest tests/test_drive_download.py -q` |
| 2 | The function returns the downloaded files as `Path` objects | `tests/test_drive_download.py:test_download_drive_folder_returns_downloaded_paths` | unit | PASS | same |
| 3 | A gdown failure (`FileURLRetrievalError`, a `DownloadError` subclass) is wrapped in `DriveDownloadError` | `tests/test_drive_download.py:test_download_drive_folder_raises_on_gdown_failure` | unit | PASS | same |
| 4 | `bookworm fetch-drive URL --output-dir DIR` downloads and prints `{"downloaded": N, "output_dir": DIR}` | `tests/test_cli.py:test_fetch_drive_downloads_and_prints_summary` | integration (CLI) | PASS | `uv run pytest tests/test_cli.py -q` |
| 5 | Without `--output-dir`, files go to `dataset/drive` | `tests/test_cli.py:test_fetch_drive_uses_dataset_drive_as_default_output_dir` | integration (CLI) | PASS | same |
| 6 | A `DriveDownloadError` from the download exits the CLI non-zero | `tests/test_cli.py:test_fetch_drive_reports_a_failed_download_with_a_nonzero_exit` | integration (CLI) | PASS | same |

## Coverage and known gaps

```
$ uv run pytest tests/test_drive_download.py tests/test_cli.py -q --cov=bookworm.drive_download --cov=bookworm.cli --cov-report=term-missing
src/bookworm/cli.py                 57      4    93%   42-43, 94-95   (pre-existing gaps, unrelated to this change)
src/bookworm/drive_download.py      16      0   100%
```

Known gaps: `gdown.download_folder` itself (network I/O, HTML scraping of the Drive share page, resume-by-size skip logic) is not exercised — it's monkeypatched out in every test. That behavior is gdown's own responsibility; nothing in this change re-implements it. No end-to-end test hits a real Drive folder.

## Merge evidence

Checkpoint commits on `main`:
- `test: add reproducer for bookworm fetch-drive` (RED) — `079f001`
- `fix: add bookworm fetch-drive command` (GREEN) — `0b5453b`

No refactor step was needed; the first implementation matched existing repo conventions (see `cli.py`'s `scan`/`annotate`/`annotator` commands and `logging_setup.log_call`) with no duplication to remove.

## Follow-up: filename-collision data loss (T16 / B2)

Live-testing `bookworm fetch-drive` against a real, user-provided Drive folder (not covered by the mocked unit tests above, which used uniquely-named fakes) found the reported `"downloaded"` count (32) didn't match the files actually on disk (25). The folder has 7 pairs/triples of distinct Drive files sharing an iPhone-style filename (`IMG_0034.HEIC` ×2, `IMG_0039.HEIC` ×3, etc). `gdown.download_folder`'s `resume=True` treated the second file at a colliding path as "already downloaded" and skipped it — silently dropping a distinct photo, not just renaming or deduplicating a true duplicate.

User chose (via `AskUserQuestion`): auto-disambiguate colliding files by prefixing the Drive file ID, rather than failing loudly or just fixing the reported count.

RED (before the fix):
```
$ uv run pytest tests/test_drive_download.py -q
ImportError: cannot import name 'build_collision_safe_file_names' from 'bookworm.drive_download'
1 error in 0.09s
```

GREEN (after the fix):
```
$ uv run pytest tests/test_drive_download.py tests/test_cli.py -q
................                                                         [100%]
16 passed in 2.58s
$ uv run pytest -q -m "not slow"
252 passed, 37 deselected, 2 warnings in 0.74s
```
(The deselected count rose from 12 to 37 only because the live test run populated `dataset/drive/` with ~25 real photos, which `tests/test_real_photos.py` parametrizes over as `@pytest.mark.slow` cases — expected, not a regression.)

Additional test specification:

| # | What is guaranteed | Test | Result |
|---|---|---|---|
| 7 | Unique file names are left unchanged | `test_build_collision_safe_file_names_keeps_unique_names_as_is` | PASS |
| 8 | Every file sharing a name with another file (2-way or 3-way) gets its Drive file ID prefixed | `test_build_collision_safe_file_names_prefixes_every_file_sharing_a_name` | PASS |
| 9 | The folder is listed (`skip_download=True`) before any file is downloaded | `test_download_drive_folder_lists_before_downloading` | PASS |
| 10 | Each listed file is downloaded individually to `output_dir/<name>` and the full list of local paths is returned | `test_download_drive_folder_downloads_each_file_and_returns_local_paths` | PASS |
| 11 | Colliding files are saved as `output_dir/<id>_<name>`, not overwriting or skipping each other | `test_download_drive_folder_prefixes_colliding_files_with_their_drive_id` | PASS |
| 12 | Parent directories are created for entries nested in a subfolder | `test_download_drive_folder_creates_parent_directories_for_nested_entries` | PASS |
| 13 | A listing failure raises `DriveDownloadError` | `test_download_drive_folder_raises_when_listing_fails` | PASS |
| 14 | A per-file download failure raises `DriveDownloadError` | `test_download_drive_folder_raises_when_a_file_fails_to_download` | PASS |

Known gap carried over from the live test: re-fetching an individual Drive file via `gdown.download(id=...)` can hit Google's own "too many accesses" throttle on that specific file ID if it's been requested repeatedly in a short window (observed firsthand while debugging this issue — two manual single-file probes against two different, previously-untouched IDs both failed this way). This is a Drive-side limitation, not something introduced by this change; it surfaces as a `DriveDownloadError` (retryable later) rather than corrupting the run. Traceback recorded as `T16` in `CLAUDE.md`.

New checkpoint commits on `main`:
- `test: add reproducer for Drive filename collisions (RED)` — `150a26c`
- `fix: prefix colliding Drive file names with their file ID` (GREEN) — `74b2cc3`
