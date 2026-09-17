from dataclasses import dataclass
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bookworm.logging_setup import log_call
from bookworm.training_dashboard.baseline_metrics import find_or_compute_baseline_metrics
from bookworm.training_dashboard.metrics_reading import EpochMetrics, find_latest_results_csv, read_epoch_metrics
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

    @app.get("/api/metrics")
    def get_training_metrics() -> list[EpochMetrics]:
        with log_call(logger, "get_training_metrics", runs_dir=str(runs_dir)):
            results_csv = find_latest_results_csv(runs_dir)
            return read_epoch_metrics(results_csv) if results_csv is not None else []

    @app.get("/api/run-info")
    def get_run_info() -> RunInfo:
        with log_call(logger, "get_run_info", runs_dir=str(runs_dir)):
            results_csv = find_latest_results_csv(runs_dir)
            if results_csv is None:
                return RunInfo(run_name=None, params={}, baseline=None)
            run_dir = results_csv.parent
            params = read_training_params(run_dir)
            return RunInfo(run_name=run_dir.name, params=params, baseline=read_baseline_if_available(run_dir, params))

    return app


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
