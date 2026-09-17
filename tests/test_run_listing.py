import os
import time
from pathlib import Path

from bookworm.training_dashboard.run_listing import RunSummary, list_run_summaries

RESULTS_CSV_HEADER = (
    "epoch,time,train/box_loss,train/cls_loss,train/dfl_loss,"
    "metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),"
    "val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0,lr/pg1,lr/pg2\n"
)


def write_run(run_dir: Path, rows: list[str], args_yaml: str | None = None) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    results_csv = run_dir / "results.csv"
    results_csv.write_text(RESULTS_CSV_HEADER + "".join(f"{row}\n" for row in rows))
    if args_yaml is not None:
        (run_dir / "args.yaml").write_text(args_yaml)
    return results_csv


def test_list_run_summaries_returns_empty_list_when_no_run_exists(tmp_path: Path) -> None:
    assert list_run_summaries(tmp_path / "runs") == []


def test_list_run_summaries_describes_a_run_without_total_epochs(tmp_path: Path) -> None:
    write_run(
        tmp_path / "runs" / "detect" / "train",
        [
            "1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001",
            "2,1,0.4,0.3,0.2,0.91,0.81,0.86,0.61,0.45,0.35,0.25,0.001,0.001,0.001",
        ],
    )

    summaries = list_run_summaries(tmp_path / "runs")

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.name == "train"
    assert summary.last_epoch == 2
    assert summary.epoch_count == 2
    assert summary.total_epochs is None
    assert isinstance(summary.updated_at, float)


def test_list_run_summaries_includes_total_epochs_from_args_yaml(tmp_path: Path) -> None:
    write_run(
        tmp_path / "runs" / "detect" / "train",
        ["1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001"],
        args_yaml="epochs: 50\n",
    )

    summaries = list_run_summaries(tmp_path / "runs")

    assert summaries[0].total_epochs == 50


def test_list_run_summaries_sorts_most_recently_modified_first(tmp_path: Path) -> None:
    older_csv = write_run(tmp_path / "runs" / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    newer_csv = write_run(tmp_path / "runs" / "detect" / "train2", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    now = time.time()
    os.utime(older_csv, (now - 100, now - 100))
    os.utime(newer_csv, (now, now))

    summaries = list_run_summaries(tmp_path / "runs")

    assert [summary.name for summary in summaries] == ["train2", "train"]


def test_run_summary_is_a_frozen_dataclass() -> None:
    summary = RunSummary(name="train", last_epoch=1, epoch_count=1, total_epochs=None, updated_at=0.0)
    assert summary.name == "train"
