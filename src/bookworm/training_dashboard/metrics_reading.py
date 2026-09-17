import csv
from dataclasses import dataclass
from pathlib import Path

import structlog

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

RESULTS_CSV_NAME = "results.csv"
TRAIN_LOSS_PREFIX = "train/"
VAL_LOSS_PREFIX = "val/"
VAL_METRIC_PREFIX = "metrics/"


@dataclass(frozen=True)
class EpochMetrics:
    epoch: int
    train_losses: dict[str, float]
    val_losses: dict[str, float]
    val_metrics: dict[str, float]


def find_all_results_csvs(runs_dir: Path) -> list[Path]:
    if not runs_dir.is_dir():
        return []
    return sorted(runs_dir.rglob(RESULTS_CSV_NAME), key=lambda path: path.stat().st_mtime, reverse=True)


def find_latest_results_csv(runs_dir: Path) -> Path | None:
    results_csv_paths = find_all_results_csvs(runs_dir)
    return results_csv_paths[0] if results_csv_paths else None


def find_results_csv_by_run_name(runs_dir: Path, run_name: str) -> Path | None:
    return next((path for path in find_all_results_csvs(runs_dir) if path.parent.name == run_name), None)


def strip_prefix_keys(row: dict[str, str], prefix: str) -> dict[str, float]:
    return {key.removeprefix(prefix): round(float(value), 4) for key, value in row.items() if key.startswith(prefix)}


def parse_epoch_row(row: dict[str, str]) -> EpochMetrics:
    return EpochMetrics(
        epoch=int(row["epoch"]),
        train_losses=strip_prefix_keys(row, TRAIN_LOSS_PREFIX),
        val_losses=strip_prefix_keys(row, VAL_LOSS_PREFIX),
        val_metrics=strip_prefix_keys(row, VAL_METRIC_PREFIX),
    )


def read_epoch_metrics(results_csv: Path) -> list[EpochMetrics]:
    with log_call(logger, "read_epoch_metrics", results_csv=str(results_csv)):
        with results_csv.open(newline="", encoding="utf-8") as csv_file:
            epochs = []
            for row in csv.DictReader(csv_file):
                try:
                    epochs.append(parse_epoch_row(row))
                except (KeyError, ValueError):
                    continue
        logger.info("epoch_metrics_read", results_csv=str(results_csv), epoch_count=len(epochs))
    return epochs
