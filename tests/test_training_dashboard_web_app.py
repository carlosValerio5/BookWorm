from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bookworm.training_dashboard import web_app as web_app_module
from bookworm.training_dashboard.web_app import create_dashboard_app

RESULTS_CSV_HEADER = (
    "epoch,time,train/box_loss,train/cls_loss,train/dfl_loss,"
    "metrics/precision(B),metrics/recall(B),metrics/mAP50(B),metrics/mAP50-95(B),"
    "val/box_loss,val/cls_loss,val/dfl_loss,lr/pg0,lr/pg1,lr/pg2\n"
)


@pytest.fixture
def runs_dir(tmp_path: Path) -> Path:
    return tmp_path / "runs"


@pytest.fixture
def client(runs_dir: Path) -> TestClient:
    return TestClient(create_dashboard_app(runs_dir))


def write_results_csv(run_dir: Path, rows: list[str]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    results_csv = run_dir / "results.csv"
    results_csv.write_text(RESULTS_CSV_HEADER + "".join(f"{row}\n" for row in rows))
    return results_csv


def write_args_yaml(run_dir: Path, content: str) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    args_path = run_dir / "args.yaml"
    args_path.write_text(content)
    return args_path


def test_index_page_is_served(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "BookWorm" in response.text


def test_static_script_is_served(client: TestClient) -> None:
    response = client.get("/static/dashboard.js")

    assert response.status_code == 200


def test_static_stylesheet_is_served(client: TestClient) -> None:
    response = client.get("/static/dashboard.css")

    assert response.status_code == 200


def test_metrics_endpoint_returns_empty_list_before_any_run(client: TestClient) -> None:
    response = client.get("/api/metrics")

    assert response.status_code == 200
    assert response.json() == []


def test_metrics_endpoint_returns_parsed_epochs_once_a_run_exists(client: TestClient, runs_dir: Path) -> None:
    write_results_csv(
        runs_dir / "detect" / "train",
        ["1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001"],
    )

    response = client.get("/api/metrics")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["epoch"] == 1
    assert body[0]["train_losses"] == {"box_loss": 0.5, "cls_loss": 0.4, "dfl_loss": 0.3}
    assert body[0]["val_losses"] == {"box_loss": 0.55, "cls_loss": 0.45, "dfl_loss": 0.35}
    assert body[0]["val_metrics"] == {"precision(B)": 0.9, "recall(B)": 0.8, "mAP50(B)": 0.85, "mAP50-95(B)": 0.6}


def test_metrics_endpoint_reflects_the_most_recently_modified_run(client: TestClient, runs_dir: Path) -> None:
    import os
    import time

    older_csv = write_results_csv(runs_dir / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    newer_csv = write_results_csv(runs_dir / "detect" / "train2", ["7,1,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2"])
    now = time.time()
    os.utime(older_csv, (now - 100, now - 100))
    os.utime(newer_csv, (now, now))

    response = client.get("/api/metrics")

    assert response.status_code == 200
    assert response.json()[0]["epoch"] == 7


def test_metrics_endpoint_scopes_to_the_requested_run(client: TestClient, runs_dir: Path) -> None:
    write_results_csv(runs_dir / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    write_results_csv(runs_dir / "detect" / "train2", ["7,1,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2"])

    response = client.get("/api/metrics", params={"run": "train"})

    assert response.status_code == 200
    assert response.json()[0]["epoch"] == 1


def test_metrics_endpoint_returns_empty_list_for_an_unknown_run(client: TestClient, runs_dir: Path) -> None:
    write_results_csv(runs_dir / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])

    response = client.get("/api/metrics", params={"run": "does-not-exist"})

    assert response.status_code == 200
    assert response.json() == []


def test_runs_endpoint_returns_empty_list_before_any_run(client: TestClient) -> None:
    response = client.get("/api/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_runs_endpoint_lists_every_run_most_recent_first(client: TestClient, runs_dir: Path) -> None:
    import os
    import time

    older_csv = write_results_csv(runs_dir / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    write_args_yaml(runs_dir / "detect" / "train", "epochs: 5\n")
    newer_csv = write_results_csv(runs_dir / "detect" / "train2", ["3,1,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2"])
    now = time.time()
    os.utime(older_csv, (now - 100, now - 100))
    os.utime(newer_csv, (now, now))

    response = client.get("/api/runs")

    assert response.status_code == 200
    body = response.json()
    assert [run["name"] for run in body] == ["train2", "train"]
    assert body[1] == {"name": "train", "last_epoch": 1, "epoch_count": 1, "total_epochs": 5, "updated_at": pytest.approx(older_csv.stat().st_mtime)}
    assert body[0]["last_epoch"] == 3
    assert body[0]["total_epochs"] is None


def test_run_info_scopes_to_the_requested_run(client: TestClient, runs_dir: Path) -> None:
    write_results_csv(runs_dir / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])
    write_args_yaml(runs_dir / "detect" / "train", "epochs: 5\n")
    write_results_csv(runs_dir / "detect" / "train2", ["3,1,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2"])
    write_args_yaml(runs_dir / "detect" / "train2", "epochs: 50\n")

    response = client.get("/api/run-info", params={"run": "train"})

    assert response.status_code == 200
    body = response.json()
    assert body["run_name"] == "train"
    assert body["params"] == {"epochs": 5}


def test_run_info_returns_empty_shape_for_an_unknown_run(client: TestClient, runs_dir: Path) -> None:
    write_results_csv(runs_dir / "detect" / "train", ["1,1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1,0.1"])

    response = client.get("/api/run-info", params={"run": "does-not-exist"})

    assert response.status_code == 200
    assert response.json() == {"run_name": None, "params": {}, "baseline": None}


def test_run_info_returns_empty_shape_before_any_run(client: TestClient) -> None:
    response = client.get("/api/run-info")

    assert response.status_code == 200
    assert response.json() == {"run_name": None, "params": {}, "baseline": None}


def test_run_info_returns_params_with_no_baseline_when_args_have_no_model_or_data(
    client: TestClient, runs_dir: Path
) -> None:
    write_results_csv(runs_dir / "detect" / "train", ["1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001"])
    write_args_yaml(runs_dir / "detect" / "train", "epochs: 5\n")

    response = client.get("/api/run-info")

    assert response.status_code == 200
    body = response.json()
    assert body["run_name"] == "train"
    assert body["params"] == {"epochs": 5}
    assert body["baseline"] is None


def test_run_info_includes_baseline_when_model_and_data_are_known(
    client: TestClient, runs_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_results_csv(runs_dir / "detect" / "train", ["1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001"])
    write_args_yaml(runs_dir / "detect" / "train", "model: models/yolo26n.pt\ndata: dataset/yolo/data.yaml\nepochs: 5\n")
    baseline_calls: list[tuple[Path, Path, Path]] = []

    def fake_find_or_compute_baseline_metrics(run_dir: Path, base_weights: Path, dataset_yaml: Path) -> dict[str, float]:
        baseline_calls.append((run_dir, base_weights, dataset_yaml))
        return {"precision(B)": 0.1, "recall(B)": 0.2, "mAP50(B)": 0.3, "mAP50-95(B)": 0.05}

    monkeypatch.setattr(web_app_module, "find_or_compute_baseline_metrics", fake_find_or_compute_baseline_metrics)

    response = client.get("/api/run-info")

    assert response.status_code == 200
    body = response.json()
    assert body["baseline"] == {"precision(B)": 0.1, "recall(B)": 0.2, "mAP50(B)": 0.3, "mAP50-95(B)": 0.05}
    assert baseline_calls == [(runs_dir / "detect" / "train", Path("models/yolo26n.pt"), Path("dataset/yolo/data.yaml"))]


def test_run_info_returns_null_baseline_when_baseline_computation_fails(
    client: TestClient, runs_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_results_csv(runs_dir / "detect" / "train", ["1,1,0.5,0.4,0.3,0.9,0.8,0.85,0.6,0.55,0.45,0.35,0.001,0.001,0.001"])
    write_args_yaml(runs_dir / "detect" / "train", "model: models/missing.pt\ndata: dataset/yolo/data.yaml\n")

    def failing_find_or_compute_baseline_metrics(run_dir: Path, base_weights: Path, dataset_yaml: Path) -> dict[str, float]:
        raise FileNotFoundError("weights file is gone")

    monkeypatch.setattr(web_app_module, "find_or_compute_baseline_metrics", failing_find_or_compute_baseline_metrics)

    response = client.get("/api/run-info")

    assert response.status_code == 200
    assert response.json()["baseline"] is None
