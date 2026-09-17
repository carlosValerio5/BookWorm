from dataclasses import dataclass
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bookworm.logging_setup import log_call
from bookworm.training_dashboard.baseline_metrics import find_or_compute_baseline_metrics
from bookworm.training_dashboard.metrics_reading import (
    EpochMetrics,
    find_latest_results_csv,
    find_results_csv_by_run_name,
    read_epoch_metrics,
)
from bookworm.training_dashboard.run_listing import RunSummary, list_run_summaries
from bookworm.training_dashboard.training_params import read_training_params

logger = structlog.stdlib.get_logger(__name__)

STATIC_DIRECTORY = Path(__file__).parent / "static"


@dataclass(frozen=True)
class RunInfo:
    run_name: str | None
    params: dict[str, str | int | float]
    baseline: dict[str, float] | None


def create_dashboard_app(runs_dir: Path) -> FastAPI:
    app = FastAPI(title="BookWorm Training Dashboard")
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")

    @app.get("/")
    def show_dashboard_page() -> FileResponse:
        return FileResponse(STATIC_DIRECTORY / "index.html")

    @app.get("/api/runs")
    def get_runs() -> list[RunSummary]:
        with log_call(logger, "get_runs", runs_dir=str(runs_dir)):
            return list_run_summaries(runs_dir)

    @app.get("/api/metrics")
    def get_training_metrics(run: str | None = None) -> list[EpochMetrics]:
        with log_call(logger, "get_training_metrics", runs_dir=str(runs_dir), run=run):
            results_csv = resolve_results_csv(runs_dir, run)
            return read_epoch_metrics(results_csv) if results_csv is not None else []

    @app.get("/api/run-info")
    def get_run_info(run: str | None = None) -> RunInfo:
        with log_call(logger, "get_run_info", runs_dir=str(runs_dir), run=run):
            results_csv = resolve_results_csv(runs_dir, run)
            if results_csv is None:
                return RunInfo(run_name=None, params={}, baseline=None)
            run_dir = results_csv.parent
            params = read_training_params(run_dir)
            return RunInfo(run_name=run_dir.name, params=params, baseline=read_baseline_if_available(run_dir, params))

    return app


def resolve_results_csv(runs_dir: Path, run: str | None) -> Path | None:
    return find_results_csv_by_run_name(runs_dir, run) if run else find_latest_results_csv(runs_dir)


def read_baseline_if_available(run_dir: Path, params: dict[str, str | int | float]) -> dict[str, float] | None:
    base_weights, dataset_yaml = params.get("model"), params.get("data")
    if not isinstance(base_weights, str) or not isinstance(dataset_yaml, str):
        return None
    try:
        return find_or_compute_baseline_metrics(run_dir, Path(base_weights), Path(dataset_yaml))
    except Exception:
        # A live validation run against possibly-moved files; compute_baseline_metrics's own
        # log_call already records the failure. Degrade the dashboard, don't 500 it.
        return None
