from pathlib import Path

import gdown
import gdown.exceptions
import pytest

from bookworm.drive_download import DriveDownloadError, download_drive_folder

FOLDER_URL = "https://drive.google.com/drive/folders/1ZXEhzbLRLU1giKKRJkjm8N04cO_JoYE2"


def test_download_drive_folder_calls_gdown_with_flat_output_and_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_download_folder(**kwargs: object) -> list[str]:
        captured_calls.append(kwargs)
        return []

    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)
    output_dir = tmp_path / "drive"

    download_drive_folder(FOLDER_URL, output_dir)

    assert captured_calls == [
        {
            "url": FOLDER_URL,
            "output": str(output_dir),
            "quiet": False,
            "use_cookies": False,
            "resume": True,
        }
    ]


def test_download_drive_folder_returns_downloaded_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "drive"
    downloaded_file_paths = [str(output_dir / "cover.jpg"), str(output_dir / "spine.jpg")]
    monkeypatch.setattr(gdown, "download_folder", lambda **kwargs: downloaded_file_paths)

    result = download_drive_folder(FOLDER_URL, output_dir)

    assert result == [output_dir / "cover.jpg", output_dir / "spine.jpg"]


def test_download_drive_folder_raises_on_gdown_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download_folder(**kwargs: object) -> list[str]:
        raise gdown.exceptions.FileURLRetrievalError("folder not found")

    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)

    with pytest.raises(DriveDownloadError):
        download_drive_folder(FOLDER_URL, tmp_path / "drive")
