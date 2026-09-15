import json
from pathlib import Path

import numpy as np
import pytest
import uvicorn
from fastapi import FastAPI
from image_factories import VALID_ISBN13, place_on_white_canvas, write_image
from typer.testing import CliRunner

from bookworm.cli import ImageWriteError, app, write_annotated_image

runner = CliRunner()


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
