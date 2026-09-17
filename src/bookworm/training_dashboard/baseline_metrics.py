import json
from pathlib import Path

import structlog
from ultralytics import YOLO

from bookworm.logging_setup import log_call
from bookworm.training_dashboard.metrics_reading import VAL_METRIC_PREFIX, strip_prefix_keys

logger = structlog.stdlib.get_logger(__name__)

BASELINE_CACHE_NAME = "baseline_metrics.json"


def compute_baseline_metrics(base_weights: Path, dataset_yaml: Path) -> dict[str, float]:
    with log_call(logger, "compute_baseline_metrics", base_weights=str(base_weights), dataset_yaml=str(dataset_yaml)):
        results = YOLO(base_weights).val(data=str(dataset_yaml), verbose=False)
        baseline_metrics = strip_prefix_keys(results.results_dict, VAL_METRIC_PREFIX)
        logger.info("baseline_metrics_computed", base_weights=str(base_weights), dataset_yaml=str(dataset_yaml))
    return baseline_metrics


def find_or_compute_baseline_metrics(run_dir: Path, base_weights: Path, dataset_yaml: Path) -> dict[str, float]:
    cache_path = run_dir / BASELINE_CACHE_NAME
    if cache_path.is_file():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    baseline_metrics = compute_baseline_metrics(base_weights, dataset_yaml)
    cache_path.write_text(json.dumps(baseline_metrics), encoding="utf-8")
    return baseline_metrics
