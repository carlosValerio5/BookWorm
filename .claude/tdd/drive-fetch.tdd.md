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
