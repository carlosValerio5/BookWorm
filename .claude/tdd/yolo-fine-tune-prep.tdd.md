# TDD Evidence: prepare YOLO for fine-tuning

**Source plan**: Inline plan from this conversation (`/ecc:plan`, conversational mode — no `*.plan.md` artifact written). Confirmed by the user invoking `/ecc:tdd-workflow` immediately after the plan was presented.

## User journeys

1. As a user, I want `bookworm build-yolo-dataset PHOTOS_DIR` to convert every labeled, confirmed-box photo into YOLO format (`images/<split>`, `labels/<split>/*.txt`, `data.yaml`), so I can hand it straight to `bookworm train-yolo`.
2. As a user, a photo with no annotation file yet should be skipped, not errored, since labeling is incremental.
3. As a user, the train/val split should be deterministic per photo so rebuilding the dataset as more photos get labeled doesn't reshuffle photos already placed.
4. As a user, boxes marked `confirmed=False` should not appear in the training labels.
5. As a user, HEIC photos should convert cleanly into the dataset (as JPEG), since ultralytics' own training image loader can hit the same `PIL.Image.open`-on-HEIC problem already documented for our own code (T6).
6. As a user, `bookworm train-yolo DATASET_YAML` should fine-tune starting from the existing `models/yolo26n.pt` weights and report the resulting best-weights path.

## Task report

| Task | Summary | Validation command | Result |
|---|---|---|---|
| `yolo_dataset.py` | `assign_split` (deterministic hash-based train/val split), `convert_box_to_yolo_line` (pixel box → normalized YOLO line), `build_yolo_dataset` (walks `list_photo_paths`, skips unlabeled, converts every photo through the existing `image_loading.load_image` + `cv2.imwrite` so HEIC never reaches ultralytics, writes `data.yaml` with `BoxType` enum order as class ids) | `uv run pytest tests/test_yolo_dataset.py -q` | 8 passed |
| `yolo_training.py` | `run_yolo_fine_tune`: loads `YOLO(base_weights)`, calls `.train(data=, epochs=, imgsz=)`, returns `<save_dir>/weights/best.pt`. Defaults: `models/yolo26n.pt`, 50 epochs, imgsz 640 | `uv run pytest tests/test_yolo_training.py -q` | 2 passed |
| `bookworm build-yolo-dataset` / `bookworm train-yolo` CLI commands | Wired into `cli.py`, mirroring `scan`/`annotate`/`fetch-drive`'s pattern (delegate to a module function, `typer.echo(json.dumps(...))`) | `uv run pytest tests/test_cli.py -q` | 11 passed (6 new + 5 pre-existing `fetch-drive`) |

RED (before implementation):
```
$ uv run pytest tests/test_yolo_dataset.py -q
ModuleNotFoundError: No module named 'bookworm.yolo_dataset'
$ uv run pytest tests/test_yolo_training.py tests/test_cli.py -q
ImportError: cannot import name 'yolo_training' from 'bookworm'
```

GREEN (after implementation):
```
$ uv run pytest tests/test_yolo_training.py tests/test_cli.py tests/test_yolo_dataset.py -q
.....................                                                    [100%]
21 passed in 2.55s
$ uv run pytest -q -m "not slow"
266 passed, 37 deselected, 2 warnings in 0.73s
$ uv run pytest tests/test_yolo_dataset.py tests/test_yolo_training.py tests/test_cli.py -q --cov=bookworm.yolo_dataset --cov=bookworm.yolo_training --cov=bookworm.cli --cov-report=term-missing
src/bookworm/cli.py                71      4    94%   48-49, 123-124   (pre-existing gaps in annotate/write_annotated_image, unrelated)
src/bookworm/yolo_dataset.py       71      0   100%
src/bookworm/yolo_training.py      15      0   100%
```

Live sanity check against the real photos downloaded earlier this session:
```
$ uv run bookworm build-yolo-dataset dataset/drive
{"train_count": 0, "val_count": 0, "skipped_unlabeled_count": 25, "output_dir": "dataset/yolo", "data_yaml_path": "dataset/yolo/data.yaml"}
```
Correct: no photo in `dataset/drive/` has a saved annotation yet (`labels/` doesn't exist in this repo), so everything is reported as skipped-unlabeled rather than silently producing an empty-but-"successful" dataset.

## Test specification

| # | What is guaranteed | Test | Result |
|---|---|---|---|
| 1 | `assign_split` is deterministic for the same photo path | `test_assign_split_is_deterministic` | PASS |
| 2 | `assign_split` isn't degenerate (produces both train and val across varied inputs) | `test_assign_split_produces_both_train_and_val` | PASS |
| 3 | A pixel `BoundingBox` normalizes to the exact expected YOLO line for a given `BoxType`/photo size | `test_convert_box_to_yolo_line_normalizes_to_photo_dimensions` | PASS |
| 4 | An unlabeled photo is skipped and counted, not errored | `test_build_yolo_dataset_skips_photos_with_no_annotation` | PASS |
| 5 | A labeled photo's image and label land in the split `assign_split` picks for it | `test_build_yolo_dataset_writes_image_and_label_in_the_assigned_split` | PASS |
| 6 | `confirmed=False` boxes are excluded from the written label file | `test_build_yolo_dataset_drops_unconfirmed_boxes` | PASS |
| 7 | A HEIC source photo converts to a valid, decodable JPEG in the dataset | `test_build_yolo_dataset_converts_heic_photos_to_jpeg` | PASS |
| 8 | `data.yaml` has the 7 `BoxType` names in enum order as class ids 0-6, and correct `train`/`val` paths | `test_build_yolo_dataset_writes_data_yaml_with_class_names_in_enum_order` | PASS |
| 9 | `run_yolo_fine_tune` passes explicit `base_weights`/`epochs`/`image_size` through to `YOLO(...)`/`.train(...)` and derives `best.pt` from `results.save_dir` | `test_run_yolo_fine_tune_passes_explicit_options_through` | PASS |
| 10 | `run_yolo_fine_tune` uses its documented defaults when not overridden | `test_run_yolo_fine_tune_uses_defaults_when_not_given` | PASS |
| 11 | `bookworm build-yolo-dataset` wires default `labels`/`dataset/yolo` dirs and prints the summary as JSON | `test_build_yolo_dataset_command_prints_the_summary` | PASS |
| 12 | `bookworm train-yolo` uses default base-weights/epochs/imgsz when not given | `test_train_yolo_command_uses_default_options` | PASS |
| 13 | `bookworm train-yolo` passes explicit `--epochs`/`--imgsz`/`--base-weights` through | `test_train_yolo_command_passes_through_explicit_options` | PASS |

## Coverage and known gaps

100% on `yolo_dataset.py` and `yolo_training.py`; 94% on `cli.py` (two pre-existing gaps in `annotate`/`write_annotated_image`, unrelated to this change).

Known, intentional gap: no test calls the real `ultralytics.YOLO(...).train(...)` — every test mocks it out. This matches the plan's stated scope: an actual training run is slow, needs real (currently nonexistent) labeled data, and is integration/manual-verification territory, not a unit test. `run_yolo_fine_tune`'s contract (what gets passed to `YOLO`/`.train`, how `best.pt` is derived) is fully covered; whether an actual training run converges to something useful is a modeling question the user answers by running it, not something a unit test can assert.

Also not covered by tests: the actual end-to-end path from `bookworm annotator` → real labels → `build-yolo-dataset` → `train-yolo` → swapping `book_detection.py`'s weights path. `labels/` doesn't exist in this repo yet (confirmed via the live sanity check above), so that full loop can't be exercised until photos are actually annotated.

## Merge evidence

Checkpoint commits on `main`:
- `test: add reproducer for YOLO dataset conversion (RED)` — `a9f22fe`
- `fix: add yolo_dataset conversion module` (GREEN) — `59bf1d3`
- `test: add reproducers for yolo_training module and its CLI commands (RED)` — `5bc70a7`
- `fix: add yolo_training module and wire both YOLO commands into the CLI` (GREEN) — `a07f5d9`

No separate refactor commit was needed; both implementations matched existing repo conventions (typer command pattern in `cli.py`, `log_call` logging, dataclass summaries) on the first pass.
