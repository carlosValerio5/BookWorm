import json
from pathlib import Path

import numpy as np
import pytest
import uvicorn
from fastapi import FastAPI
from image_factories import VALID_ISBN13, place_on_white_canvas, write_image
from typer.testing import CliRunner

from bookworm import cli
from bookworm.cli import ImageWriteError, app, write_annotated_image
from bookworm.drive_download import DriveDownloadError

runner = CliRunner()

FOLDER_URL = "https://drive.google.com/drive/folders/1ZXEhzbLRLU1giKKRJkjm8N04cO_JoYE2"


def test_annotator_rejects_missing_photos_folder(tmp_path: Path) -> None:
    result = runner.invoke(app, ["annotator", str(tmp_path / "missing")])

    assert result.exit_code == 2


def test_annotator_serves_app_on_localhost_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uvicorn_calls: list[tuple[object, dict[str, object]]] = []
    monkeypatch.setattr(uvicorn, "run", lambda served_app, **options: uvicorn_calls.append((served_app, options)))

    result = runner.invoke(app, ["annotator", str(tmp_path), "--labels-dir", str(tmp_path / "labels"), "--port", "9000"])

    assert result.exit_code == 0, result.output
    served_app, options = uvicorn_calls[0]
    assert isinstance(served_app, FastAPI)
    assert options == {"host": "127.0.0.1", "port": 9000, "log_config": None}


def test_scan_rejects_missing_image_path(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scan", str(tmp_path / "missing.png")])

    assert result.exit_code == 2


def test_fetch_drive_downloads_and_prints_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "drive"
    downloaded_calls: list[tuple[str, Path]] = []

    def fake_download_drive_folder(folder_url: str, drive_output_dir: Path) -> list[Path]:
        downloaded_calls.append((folder_url, drive_output_dir))
        return [drive_output_dir / "cover.jpg", drive_output_dir / "spine.jpg"]

    monkeypatch.setattr(cli, "download_drive_folder", fake_download_drive_folder)

    result = runner.invoke(app, ["fetch-drive", FOLDER_URL, "--output-dir", str(output_dir)])

    assert result.exit_code == 0, result.output
    assert downloaded_calls == [(FOLDER_URL, output_dir)]
    assert json.loads(result.stdout) == {"downloaded": 2, "output_dir": str(output_dir)}


def test_fetch_drive_uses_dataset_drive_as_default_output_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_output_dirs: list[Path] = []
    monkeypatch.setattr(
        cli,
        "download_drive_folder",
        lambda folder_url, drive_output_dir: captured_output_dirs.append(drive_output_dir) or [],
    )

    result = runner.invoke(app, ["fetch-drive", FOLDER_URL])

    assert result.exit_code == 0, result.output
    assert captured_output_dirs == [Path("dataset/drive")]


def test_fetch_drive_reports_a_failed_download_with_a_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download_drive_folder(folder_url: str, drive_output_dir: Path) -> list[Path]:
        raise DriveDownloadError(f"Could not download folder {folder_url!r}")

    monkeypatch.setattr(cli, "download_drive_folder", fake_download_drive_folder)

    result = runner.invoke(app, ["fetch-drive", FOLDER_URL])

    assert result.exit_code != 0


def test_write_annotated_image_raises_when_output_folder_is_missing(tmp_path: Path, blank_image: np.ndarray) -> None:
    with pytest.raises(ImageWriteError):
        write_annotated_image(tmp_path / "missing_folder" / "annotated.png", blank_image)


@pytest.mark.slow
@pytest.mark.usefixtures("book_detector", "text_reader")
def test_annotate_writes_image_and_prints_isbn_scan(tmp_path: Path, isbn_barcode_image: np.ndarray) -> None:
    image_path = write_image(tmp_path / "barcode.png", place_on_white_canvas(isbn_barcode_image, top=80, left=80))
    output_path = tmp_path / "annotated.png"

    result = runner.invoke(app, ["annotate", str(image_path), str(output_path)])

    assert result.exit_code == 0, result.output
    assert output_path.exists()
    assert json.loads(result.stdout)["isbn"] == VALID_ISBN13
