import os
import time
from pathlib import Path

from bookworm.training_dashboard.metrics_reading import EpochMetrics, find_latest_results_csv, read_epoch_metrics

RESULTS_CSV_HEADER = (
    "epoch,time,train/box_loss,train/cls_loss,train/dfl_loss,"
    "metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),"
    "val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0,lr/pg1,lr/pg2\n"
)


def write_results_csv(run_dir: Path, rows: list[str]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    results_csv = run_dir / "results.csv"
    results_csv.write_text(RESULTS_CSV_HEADER + "".join(f"{row}\n" for row in rows))
    return results_csv


def test_find_latest_results_csv_returns_none_when_no_run_exists(tmp_path: Path) -> None:
    assert find_latest_results_csv(tmp_path / "runs") is None


def test_find_latest_results_csv_returns_none_when_runs_dir_is_empty(tmp_path: Path) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    assert find_latest_results_csv(runs_dir) is None


def test_find_latest_results_csv_returns_the_only_run(tmp_path: Path) -> None:
    results_csv = write_results_csv(tmp_path / "runs" / "detect" / "train", ["1,12.3,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001"])

    assert find_latest_results_csv(tmp_path / "runs") == results_csv


def test_find_latest_results_csv_picks_the_most_recently_modified_run(tmp_path: Path) -> None:
    older_csv = write_results_csv(tmp_path / "runs" / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    newer_csv = write_results_csv(tmp_path / "runs" / "detect" / "train2", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    now = time.time()
    os.utime(older_csv, (now - 100, now - 100))
    os.utime(newer_csv, (now, now))

    assert find_latest_results_csv(tmp_path / "runs") == newer_csv


def test_read_epoch_metrics_groups_columns_by_prefix(tmp_path: Path) -> None:
    results_csv = write_results_csv(
        tmp_path / "runs" / "detect" / "train",
        ["1,12.3,0.512300,0.412300,0.312300,0.912300,0.812300,0.852300,0.612300,0.552300,0.452300,0.352300,0.001000,0.001000,0.001000"],
    )

    epochs = read_epoch_metrics(results_csv)

    assert epochs == [
        EpochMetrics(
            epoch=1,
            train_losses={"box_loss": 0.5123, "cls_loss": 0.4123, "dfl_loss": 0.3123},
            val_losses={"box_loss": 0.5523, "cls_loss": 0.4523, "dfl_loss": 0.3523},
            val_metrics={
                "precision(B)": 0.9123,
                "recall(B)": 0.8123,
                "mAP50(B)": 0.8523,
                "mAP50-95(B)": 0.6123,
            },
        )
    ]


def test_read_epoch_metrics_reads_every_row_in_order(tmp_path: Path) -> None:
    results_csv = write_results_csv(
        tmp_path / "runs" / "detect" / "train",
        [
            "1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001",
            "2,1,0.4,0.3,0.2,0.91,0.81,0.86,0.61,0.45,0.35,0.25,0.001,0.001,0.001",
        ],
    )

    epochs = read_epoch_metrics(results_csv)

    assert [epoch.epoch for epoch in epochs] == [1, 2]


def test_read_epoch_metrics_skips_a_malformed_row(tmp_path: Path) -> None:
    results_csv = write_results_csv(
        tmp_path / "runs" / "detect" / "train",
        [
            "1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001",
            "not,a,valid,row",
            "2,1,0.4,0.3,0.2,0.91,0.81,0.86,0.61,0.45,0.35,0.25,0.001,0.001,0.001",
        ],
    )

    epochs = read_epoch_metrics(results_csv)

    assert [epoch.epoch for epoch in epochs] == [1, 2]
