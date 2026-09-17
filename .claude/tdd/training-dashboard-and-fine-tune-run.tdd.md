# TDD Evidence: training dashboard + first real fine-tune run

**Source plan**: Inline plan from this conversation (`/ecc:plan`, conversational mode — no `*.plan.md` artifact written). Confirmed by the user with "yes, proceed with /ecc:tdd-workflow".

## User journeys

1. As a user, I want to run the existing fine-tuning tool (`bookworm train-yolo`) on the now-fully-labeled dataset, so I have a checkpoint to inspect.
2. As a user, I want a dashboard styled like the annotator that shows live, per-epoch loss (train vs val) as training runs.
3. As a user, I want the same dashboard to show accuracy-style metrics — understanding that YOLO detection only computes precision/recall/mAP on the validation set, never on train, so the "accuracy" panel is honestly validation-only, not a fabricated train number.
4. As a user, before any training run exists, the dashboard should show an empty state, not an error.
5. As a user, the metrics parser shouldn't hardcode ultralytics' exact `results.csv` column names, since those can shift between versions (confirmed live: `yolo26n` writes `l1_loss`, not the `dfl_loss` seen in the ultralytics source read during planning).

## Task report

| Task | Summary | Validation command | Result |
|---|---|---|---|
| `metrics_reading.py` | `find_latest_results_csv` (most-recently-modified `results.csv` under a runs dir), `read_epoch_metrics` (parses a CSV row into `EpochMetrics` by grouping columns on `train/`, `val/`, `metrics/` prefixes — not fixed column names) | `uv run pytest tests/test_metrics_reading.py -q` | 7 passed |
| `training_dashboard/web_app.py` | `create_dashboard_app(runs_dir)`: `GET /` serves `index.html`, `/static` mount, `GET /api/metrics` returns `[]` before any run exists, else the parsed epoch list | `uv run pytest tests/test_training_dashboard_web_app.py -q` | 6 passed |
| `training_dashboard/static/{index.html,dashboard.css,dashboard.js}` | Window-chrome layout reusing the annotator's exact `:root` design tokens; empty state before a run exists; two hand-rolled inline-SVG line charts (no chart library) — Loss (train vs val, summed loss components) and "Accuracy (validation)" (precision/recall/mAP50/mAP50-95); polls `/api/metrics` every 2s | covered indirectly by `test_training_dashboard_web_app.py` (static files served) + live browser check below | PASS |
| `bookworm dashboard` CLI command | Mirrors the `annotator` command: builds the app via the factory, `uvicorn.run(..., host=127.0.0.1)`, default port 8766 (distinct from the annotator's 8765), default `runs/` dir | `uv run pytest tests/test_cli.py -k dashboard -q` | 2 passed |
| `.gitignore` | Added `runs/` (was not ignored; would have leaked training weights/plots into git) | — | n/a (config) |
| `CHANGELOG.md` | Added `[Unreleased]` line for `bookworm dashboard` (F2) | — | n/a (docs) |
| Real fine-tune run | `bookworm train-yolo dataset/yolo/data.yaml --epochs 5` against the real (tiny, 4-image) labeled dataset | `uv run bookworm train-yolo dataset/yolo/data.yaml --epochs 5` | Completed, exit 0, `runs/detect/train/results.csv` written |

RED (before implementation):
```
$ uv run pytest tests/test_metrics_reading.py -q
ModuleNotFoundError: No module named 'bookworm.training_dashboard'
$ uv run pytest tests/test_training_dashboard_web_app.py -q
ModuleNotFoundError: No module named 'bookworm.training_dashboard.web_app'
$ uv run pytest tests/test_cli.py -k dashboard -q
No such command 'dashboard'.
```

GREEN (after implementation):
```
$ uv run pytest -q -m "not slow"
293 passed, 39 deselected, 2 warnings in 3.01s
$ uv run pytest tests/test_metrics_reading.py tests/test_training_dashboard_web_app.py -q --cov=bookworm.training_dashboard --cov-report=term-missing
src/bookworm/training_dashboard/__init__.py              0      0   100%
src/bookworm/training_dashboard/metrics_reading.py      38      0   100%
src/bookworm/training_dashboard/web_app.py              21      0   100%
```

Live sanity check — real training run + browser verification:
```
$ uv run bookworm dashboard --port 8766          # background
$ uv run bookworm train-yolo dataset/yolo/data.yaml --epochs 5   # background
...
5 epochs completed in 0.002 hours.
Results saved to /Users/carlosvalerio/Desktop/Escuela/yolo/BookWorm/runs/detect/train
$ curl -s http://127.0.0.1:8766/api/metrics | python3 -m json.tool | head -20
[{"epoch": 1, "train_losses": {"box_loss": 1.9674, "cls_loss": 5.6789, "l1_loss": 0.0195}, ...}]
```
A chrome-devtools screenshot of `http://127.0.0.1:8766` after the run finished showed the dark window-chrome dashboard with "Epoch 5" in the title bar, a Loss chart with distinct train (blue) and val (orange) lines, and an "Accuracy (validation)" chart with all four series flat at 0 — expected and correct, since the 4-image dataset produced a model with 0 precision/recall/mAP, not a rendering bug.

Note: `yolo26n`'s actual `results.csv` header uses `train/l1_loss` / `val/l1_loss`, not `dfl_loss` as seen when reading the ultralytics source during planning. `metrics_reading.py`'s prefix-based grouping handled this with no code changes — validates journey 5.

## Test specification

| # | What is guaranteed | Test | Result |
|---|---|---|---|
| 1 | No `results.csv` anywhere under a nonexistent runs dir → `None` | `test_find_latest_results_csv_returns_none_when_no_run_exists` | PASS |
| 2 | Runs dir exists but is empty → `None` | `test_find_latest_results_csv_returns_none_when_runs_dir_is_empty` | PASS |
| 3 | A single run's `results.csv` is found | `test_find_latest_results_csv_returns_the_only_run` | PASS |
| 4 | Among multiple runs, the most-recently-modified `results.csv` wins | `test_find_latest_results_csv_picks_the_most_recently_modified_run` | PASS |
| 5 | A CSV row is grouped into `train_losses`/`val_losses`/`val_metrics` by column prefix, values rounded to 4dp | `test_read_epoch_metrics_groups_columns_by_prefix` | PASS |
| 6 | Every row is read back in order | `test_read_epoch_metrics_reads_every_row_in_order` | PASS |
| 7 | A malformed row is skipped, not fatal | `test_read_epoch_metrics_skips_a_malformed_row` | PASS |
| 8 | `GET /` serves the dashboard page | `test_index_page_is_served` | PASS |
| 9 | `GET /static/dashboard.js` and `/static/dashboard.css` are served | `test_static_script_is_served`, `test_static_stylesheet_is_served` | PASS |
| 10 | `GET /api/metrics` returns `[]` before any run exists (not a 404) | `test_metrics_endpoint_returns_empty_list_before_any_run` | PASS |
| 11 | `GET /api/metrics` returns parsed epoch data once a run exists | `test_metrics_endpoint_returns_parsed_epochs_once_a_run_exists` | PASS |
| 12 | `GET /api/metrics` reflects the most-recently-modified run when several exist | `test_metrics_endpoint_reflects_the_most_recently_modified_run` | PASS |
| 13 | `bookworm dashboard` binds to `127.0.0.1` and passes `--runs-dir`/`--port` through | `test_dashboard_serves_app_on_localhost_only` | PASS |
| 14 | `bookworm dashboard` uses default runs dir (`runs/`) and port (`8766`) when not given | `test_dashboard_uses_default_runs_dir_and_port` | PASS |

## Coverage and known gaps

100% on `metrics_reading.py` and `web_app.py`. No dedicated JS unit tests for `dashboard.js` — it's exercised indirectly (static file served, correct DOM ids referenced) and directly via the live browser check above; the project has no JS test runner for this static-page style of code (same as the existing `annotator.js`, which is covered only by `tests/js/box_geometry.test.js` for its pure-function helpers, not the DOM-wiring code).

Known, intentional scope limit (flagged in the plan before implementation): the fine-tune run used `--epochs 5` against a 4-image dataset (3 train / 1 val) as a pipeline smoke test, not a real model — precision/recall/mAP are 0 across all 5 epochs, which is the honest, expected result of that dataset size, not a defect in the dashboard or the training call.

## Merge evidence

Checkpoint commits on `main`:
- `test: add reproducer for training dashboard metrics reader` (RED) — `b2cfb893`
- `fix: add training dashboard metrics reader` (GREEN) — `ecf7b1a3`
- `test: add reproducer for training dashboard web app` (RED) — `efe38c03`
- `fix: add training dashboard web app and frontend` (GREEN) — `0339e157`
- `test: add reproducer for bookworm dashboard CLI command` (RED) — `494e3b38`
- `fix: wire bookworm dashboard CLI command` (GREEN) — `a2bfb63f`
- `test: cover empty runs directory in metrics reader` (additional coverage) — `c66befcb`
- `docs: ignore runs/ and note bookworm dashboard in changelog` — `45a8bc8d`

No separate refactor commit was needed; both implementations matched existing repo conventions (`log_call` logging, FastAPI factory + `/static` mount pattern from `annotator/web_app.py`, typer command pattern from `cli.py`) on the first pass. One test-authoring mistake was caught and fixed during RED→GREEN (miscounted CSV columns in the first version of `test_read_epoch_metrics_groups_columns_by_prefix`'s expected values) — corrected in the same GREEN commit rather than treated as an implementation bug, since the implementation's grouping matched the real header order.
