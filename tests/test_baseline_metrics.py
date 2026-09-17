import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from bookworm.training_dashboard import baseline_metrics
from bookworm.training_dashboard.baseline_metrics import (
    BASELINE_CACHE_NAME,
    compute_baseline_metrics,
    find_or_compute_baseline_metrics,
)

FAKE_RESULTS_DICT = {
    "metrics/precision(B)": 0.512345,
    "metrics/recall(B)": 0.412345,
    "metrics/mAP50(B)": 0.612345,
    "metrics/mAP50-95(B)": 0.312345,
    "fitness": 0.4,
}


def install_fake_yolo(monkeypatch: pytest.MonkeyPatch) -> tuple[list[object], list[dict[str, object]]]:
    constructor_calls: list[object] = []
    val_calls: list[dict[str, object]] = []

    class FakeYolo:
        def __init__(self, weights: object) -> None:
            constructor_calls.append(weights)

        def val(self, **kwargs: object) -> SimpleNamespace:
            val_calls.append(kwargs)
            return SimpleNamespace(results_dict=FAKE_RESULTS_DICT)

    monkeypatch.setattr(baseline_metrics, "YOLO", FakeYolo)
    return constructor_calls, val_calls


def test_compute_baseline_metrics_validates_base_weights_and_strips_metric_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    constructor_calls, val_calls = install_fake_yolo(monkeypatch)
    base_weights = tmp_path / "yolo26n.pt"
    dataset_yaml = tmp_path / "data.yaml"

    metrics = compute_baseline_metrics(base_weights, dataset_yaml)

    assert constructor_calls == [base_weights]
    assert val_calls == [{"data": str(dataset_yaml), "verbose": False}]
    assert metrics == {
        "precision(B)": 0.5123,
        "recall(B)": 0.4123,
        "mAP50(B)": 0.6123,
        "mAP50-95(B)": 0.3123,
    }


def test_find_or_compute_baseline_metrics_computes_and_caches_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_yolo(monkeypatch)
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    metrics = find_or_compute_baseline_metrics(run_dir, tmp_path / "yolo26n.pt", tmp_path / "data.yaml")

    assert metrics["precision(B)"] == 0.5123
    cache_path = run_dir / BASELINE_CACHE_NAME
    assert cache_path.is_file()
    assert json.loads(cache_path.read_text()) == metrics


def test_find_or_compute_baseline_metrics_uses_the_cache_without_calling_yolo_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("YOLO should not be constructed when a cache exists")

    monkeypatch.setattr(baseline_metrics, "YOLO", fail_if_called)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    cached_metrics = {"precision(B)": 0.9, "recall(B)": 0.9, "mAP50(B)": 0.9, "mAP50-95(B)": 0.9}
    (run_dir / BASELINE_CACHE_NAME).write_text(json.dumps(cached_metrics))

    metrics = find_or_compute_baseline_metrics(run_dir, tmp_path / "yolo26n.pt", tmp_path / "data.yaml")

    assert metrics == cached_metrics
