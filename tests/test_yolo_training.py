from pathlib import Path
from types import SimpleNamespace

import pytest

from bookworm import yolo_training
from bookworm.yolo_training import (
    DEFAULT_BASE_WEIGHTS,
    DEFAULT_BATCH_SIZE,
    DEFAULT_EPOCHS,
    DEFAULT_IMAGE_SIZE,
    run_yolo_fine_tune,
)


def install_fake_yolo(monkeypatch: pytest.MonkeyPatch, save_dir: Path) -> tuple[list[object], list[dict[str, object]]]:
    constructor_calls: list[object] = []
    train_calls: list[dict[str, object]] = []

    class FakeYolo:
        def __init__(self, weights: object) -> None:
            constructor_calls.append(weights)

        def train(self, **kwargs: object) -> SimpleNamespace:
            train_calls.append(kwargs)
            return SimpleNamespace(save_dir=save_dir)

    monkeypatch.setattr(yolo_training, "YOLO", FakeYolo)
    return constructor_calls, train_calls


def test_run_yolo_fine_tune_passes_explicit_options_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    save_dir = tmp_path / "runs" / "detect" / "train3"
    constructor_calls, train_calls = install_fake_yolo(monkeypatch, save_dir)
    dataset_yaml = tmp_path / "data.yaml"
    base_weights = tmp_path / "custom.pt"

    best_weights_path = run_yolo_fine_tune(dataset_yaml, base_weights=base_weights, epochs=10, image_size=320, batch_size=8)

    assert constructor_calls == [base_weights]
    assert train_calls == [{"data": str(dataset_yaml), "epochs": 10, "imgsz": 320, "batch": 8}]
    assert best_weights_path == save_dir / "weights" / "best.pt"


def test_run_yolo_fine_tune_uses_defaults_when_not_given(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    save_dir = tmp_path / "runs" / "detect" / "train"
    constructor_calls, train_calls = install_fake_yolo(monkeypatch, save_dir)
    dataset_yaml = tmp_path / "data.yaml"

    run_yolo_fine_tune(dataset_yaml)

    assert constructor_calls == [DEFAULT_BASE_WEIGHTS]
    assert train_calls == [{"data": str(dataset_yaml), "epochs": DEFAULT_EPOCHS, "imgsz": DEFAULT_IMAGE_SIZE, "batch": DEFAULT_BATCH_SIZE}]
