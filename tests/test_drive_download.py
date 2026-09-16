from pathlib import Path

import gdown
import gdown.exceptions
import pytest
from gdown.download import GoogleDriveFileToDownload

from bookworm.drive_download import DriveDownloadError, build_collision_safe_file_names, download_drive_folder

FOLDER_URL = "https://drive.google.com/drive/folders/1ZXEhzbLRLU1giKKRJkjm8N04cO_JoYE2"


def build_entry(entry_id: str, name: str) -> GoogleDriveFileToDownload:
    return GoogleDriveFileToDownload(id=entry_id, path=name, local_path=f"/unused/{name}")


def build_fake_download_folder(entries: list[GoogleDriveFileToDownload], skip_writing_ids: set[str] | None = None):
    skip_writing_ids = skip_writing_ids or set()
    listing_calls: list[dict[str, object]] = []
    batch_calls: list[dict[str, object]] = []

    def fake_download_folder(**kwargs: object) -> list[GoogleDriveFileToDownload]:
        if kwargs.get("skip_download"):
            listing_calls.append(kwargs)
            return entries
        batch_calls.append(kwargs)
        output_dir = Path(str(kwargs["output"]))
        for entry in entries:
            if entry.id in skip_writing_ids:
                continue
            entry_path = output_dir / entry.path
            entry_path.parent.mkdir(parents=True, exist_ok=True)
            if not entry_path.exists():
                entry_path.write_bytes(b"fake-photo-bytes")
        return [entry.path for entry in entries]

    return fake_download_folder, listing_calls, batch_calls


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


def test_download_drive_folder_lists_then_batch_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "cover.jpg"), build_entry("id-b", "spine.jpg")]
    fake_download_folder, listing_calls, batch_calls = build_fake_download_folder(entries)
    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)

    download_drive_folder(FOLDER_URL, output_dir)

    assert listing_calls == [{"url": FOLDER_URL, "output": str(output_dir), "skip_download": True, "use_cookies": False}]
    assert batch_calls == [
        {"url": FOLDER_URL, "output": str(output_dir), "quiet": False, "use_cookies": False, "resume": True}
    ]


def test_download_drive_folder_returns_non_colliding_files_from_the_batch_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "cover.jpg"), build_entry("id-b", "spine.jpg")]
    fake_download_folder, _, _ = build_fake_download_folder(entries)
    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)
    monkeypatch.setattr(gdown, "download", lambda **kwargs: pytest.fail("no collision, should not need an individual download"))

    result = download_drive_folder(FOLDER_URL, output_dir)

    assert result == [output_dir / "cover.jpg", output_dir / "spine.jpg"]


def test_download_drive_folder_skips_a_file_missing_after_the_batch_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "cover.jpg"), build_entry("id-b", "spine.jpg")]
    fake_download_folder, _, _ = build_fake_download_folder(entries, skip_writing_ids={"id-a"})
    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)

    result = download_drive_folder(FOLDER_URL, output_dir)

    assert result == [output_dir / "spine.jpg"]


def test_download_drive_folder_individually_refetches_colliding_files_by_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "IMG_0034.HEIC"), build_entry("id-b", "IMG_0034.HEIC")]
    fake_download_folder, _, _ = build_fake_download_folder(entries)
    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)
    captured_download_calls: list[dict[str, object]] = []

    def fake_download(**kwargs: object) -> str:
        captured_download_calls.append(kwargs)
        Path(str(kwargs["output"])).write_bytes(b"fake-photo-bytes")
        return str(kwargs["output"])

    monkeypatch.setattr(gdown, "download", fake_download)

    result = download_drive_folder(FOLDER_URL, output_dir)

    assert result == [output_dir / "id-a_IMG_0034.HEIC", output_dir / "id-b_IMG_0034.HEIC"]
    assert captured_download_calls == [
        {
            "id": "id-a",
            "output": str(output_dir / "id-a_IMG_0034.HEIC"),
            "quiet": False,
            "use_cookies": False,
            "resume": True,
        },
        {
            "id": "id-b",
            "output": str(output_dir / "id-b_IMG_0034.HEIC"),
            "quiet": False,
            "use_cookies": False,
            "resume": True,
        },
    ]
    assert not (output_dir / "IMG_0034.HEIC").exists()


def test_download_drive_folder_skips_a_colliding_file_that_fails_to_refetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_dir = tmp_path / "drive"
    entries = [build_entry("id-a", "IMG_0034.HEIC"), build_entry("id-b", "IMG_0034.HEIC")]
    fake_download_folder, _, _ = build_fake_download_folder(entries)
    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)

    def fake_download(**kwargs: object) -> str:
        if kwargs["id"] == "id-a":
            raise gdown.exceptions.DownloadError("too many accesses")
        Path(str(kwargs["output"])).write_bytes(b"fake-photo-bytes")
        return str(kwargs["output"])

    monkeypatch.setattr(gdown, "download", fake_download)

    result = download_drive_folder(FOLDER_URL, output_dir)

    assert result == [output_dir / "id-b_IMG_0034.HEIC"]


def test_download_drive_folder_raises_when_listing_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download_folder(**kwargs: object) -> list[GoogleDriveFileToDownload]:
        raise gdown.exceptions.FileURLRetrievalError("folder not found")

    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)

    with pytest.raises(DriveDownloadError):
        download_drive_folder(FOLDER_URL, tmp_path / "drive")


def test_download_drive_folder_raises_when_the_batch_download_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entries = [build_entry("id-a", "cover.jpg")]

    def fake_download_folder(**kwargs: object) -> list[GoogleDriveFileToDownload]:
        if kwargs.get("skip_download"):
            return entries
        raise gdown.exceptions.FileURLRetrievalError("folder became unreachable")

    monkeypatch.setattr(gdown, "download_folder", fake_download_folder)

    with pytest.raises(DriveDownloadError):
        download_drive_folder(FOLDER_URL, tmp_path / "drive")
