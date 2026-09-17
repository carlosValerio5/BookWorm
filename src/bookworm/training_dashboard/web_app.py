from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from bookworm.logging_setup import log_call
from bookworm.training_dashboard.metrics_reading import EpochMetrics, find_latest_results_csv, read_epoch_metrics

logger = structlog.stdlib.get_logger(__name__)

STATIC_DIRECTORY = Path(__file__).parent / "static"


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

    return app
