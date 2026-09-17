from dataclasses import dataclass
from pathlib import Path

from bookworm.training_dashboard.metrics_reading import find_all_results_csvs, read_epoch_metrics
from bookworm.training_dashboard.training_params import read_training_params


@dataclass(frozen=True)
class RunSummary:
    name: str
    last_epoch: int
    epoch_count: int
    total_epochs: int | None
    updated_at: float


def summarize_run(results_csv: Path) -> RunSummary:
    run_dir = results_csv.parent
    epochs = read_epoch_metrics(results_csv)
    total_epochs = read_training_params(run_dir).get("epochs")
    return RunSummary(
        name=run_dir.name,
        last_epoch=epochs[-1].epoch if epochs else 0,
        epoch_count=len(epochs),
        total_epochs=total_epochs if isinstance(total_epochs, int) else None,
        updated_at=results_csv.stat().st_mtime,
    )


def list_run_summaries(runs_dir: Path) -> list[RunSummary]:
    return [summarize_run(results_csv) for results_csv in find_all_results_csvs(runs_dir)]
