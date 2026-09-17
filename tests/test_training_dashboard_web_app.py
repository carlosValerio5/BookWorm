from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
