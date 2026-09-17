from pathlib import Path

from bookworm.training_dashboard.training_params import read_training_params


def write_args_yaml(run_dir: Path, content: str) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    args_path = run_dir / "args.yaml"
    args_path.write_text(content)
    return args_path


def test_read_training_params_returns_empty_dict_when_args_yaml_is_missing(tmp_path: Path) -> None:
    assert read_training_params(tmp_path / "run") == {}


def test_read_training_params_extracts_only_the_allow_listed_keys(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    write_args_yaml(
        run_dir,
        """
        model: models/yolo26n.pt
        data: dataset/yolo/data.yaml
        epochs: 50
        batch: 16
        imgsz: 640
        optimizer: auto
        lr0: 0.01
        seed: 0
        deterministic: true
        """,
    )

    params = read_training_params(run_dir)

    assert params == {
        "model": "models/yolo26n.pt",
        "data": "dataset/yolo/data.yaml",
        "epochs": 50,
        "batch": 16,
        "imgsz": 640,
        "optimizer": "auto",
        "lr0": 0.01,
    }


def test_read_training_params_omits_keys_missing_from_args_yaml(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    write_args_yaml(run_dir, "epochs: 5\n")

    params = read_training_params(run_dir)

    assert params == {"epochs": 5}
