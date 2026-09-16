from pathlib import Path

import gdown
import gdown.exceptions
import pytest
from gdown.download import GoogleDriveFileToDownload

from bookworm.drive_download import DriveDownloadError, build_collision_safe_file_names, download_drive_folder

FOLDER_URL = "https://drive.google.com/drive/folders/1ZXEhzbLRLU1giKKRJkjm8N04cO_JoYE2"


def build_entry(entry_id: str, name: str) -> GoogleDriveFileToDownload:
    return GoogleDriveFileToDownload(id=entry_id, path=name, local_path=f"/unused/{name}")


def test_build_collision_safe_file_names_keeps_unique_names_as_is() -> None:
    entries = [build_entry("id-a", "cover.jpg"), build_entry("id-b", "spine.jpg")]

    file_names = build_collision_safe_file_names(entries)

    assert file_names == {"id-a": "cover.jpg", "id-b": "spine.jpg"}


def test_build_collision_safe_file_names_prefixes_every_file_sharing_a_name() -> None:
    entries = [
        build_entry("id-a", "IMG_0034.HEIC"),
        build_entry("id-b", "IMG_0034.HEIC"),
        build_entry("id-c", "IMG_0039.HEIC"),
        build_entry("id-d", "IMG_0039.HEIC"),
        build_entry("id-e", "IMG_0039.HEIC"),
    ]

    file_names = build_collision_safe_file_names(entries)

    assert file_names == {
        "id-a": "id-a_IMG_0034.HEIC",
        "id-b": "id-b_IMG_0034.HEIC",
        "id-c": "id-c_IMG_0039.HEIC",
        "id-d": "id-d_IMG_0039.HEIC",
        "id-e": "id-e_IMG_0039.HEIC",
    }


def test_download_drive_folder_lists_before_downloading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured_listing_calls: list[dict[str, object]] = []

    def fake_download_folder(**kwargs: object) -> list[GoogleDriveFileToDownload]:
        captured_listing_calls.append(kwargs)
        return []

    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)
    output_dir = tmp_path / "drive"

    download_drive_folder(FOLDER_URL, output_dir)

    assert captured_listing_calls == [
        {"url": FOLDER_URL, "output": str(output_dir), "skip_download": True, "use_cookies": False}
    ]


def test_download_drive_folder_downloads_each_file_and_returns_local_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "cover.jpg"), build_entry("id-b", "spine.jpg")]
    monkeypatch.setattr(gdown, "download_folder", lambda **kwargs: entries)
    captured_download_calls: list[dict[str, object]] = []

    def fake_download(**kwargs: object) -> str:
        captured_download_calls.append(kwargs)
        return str(kwargs["output"])

    monkeypatch.setattr(gdown, "download", fake_download)

    result = download_drive_folder(FOLDER_URL, output_dir)

    assert result == [output_dir / "cover.jpg", output_dir / "spine.jpg"]
    assert captured_download_calls == [
        {"id": "id-a", "output": str(output_dir / "cover.jpg"), "quiet": False, "use_cookies": False, "resume": True},
        {"id": "id-b", "output": str(output_dir / "spine.jpg"), "quiet": False, "use_cookies": False, "resume": True},
    ]


def test_download_drive_folder_prefixes_colliding_files_with_their_drive_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "IMG_0034.HEIC"), build_entry("id-b", "IMG_0034.HEIC")]
    monkeypatch.setattr(gdown, "download_folder", lambda **kwargs: entries)
    monkeypatch.setattr(gdown, "download", lambda **kwargs: str(kwargs["output"]))

    result = download_drive_folder(FOLDER_URL, output_dir)

    assert result == [output_dir / "id-a_IMG_0034.HEIC", output_dir / "id-b_IMG_0034.HEIC"]


def test_download_drive_folder_creates_parent_directories_for_nested_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "book-hauls/cover.jpg")]
    monkeypatch.setattr(gdown, "download_folder", lambda **kwargs: entries)
    monkeypatch.setattr(gdown, "download", lambda **kwargs: str(kwargs["output"]))

    download_drive_folder(FOLDER_URL, output_dir)

    assert (output_dir / "book-hauls").is_dir()


def test_download_drive_folder_raises_when_listing_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download_folder(**kwargs: object) -> list[GoogleDriveFileToDownload]:
        raise gdown.exceptions.FileURLRetrievalError("folder not found")

    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)

    with pytest.raises(DriveDownloadError):
        download_drive_folder(FOLDER_URL, tmp_path / "drive")


def test_download_drive_folder_raises_when_a_file_fails_to_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = [build_entry("id-a", "cover.jpg")]
    monkeypatch.setattr(gdown, "download_folder", lambda **kwargs: entries)

    def fake_download(**kwargs: object) -> str:
        raise gdown.exceptions.DownloadError("too many accesses")

    monkeypatch.setattr(gdown, "download", fake_download)

    with pytest.raises(DriveDownloadError):
        download_drive_folder(FOLDER_URL, tmp_path / "drive")
