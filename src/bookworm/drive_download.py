from collections import Counter
from pathlib import Path
from typing import cast

import gdown
import gdown.exceptions
import structlog
from gdown.download import GoogleDriveFileToDownload

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)


class DriveDownloadError(Exception):
    pass


def build_collision_safe_file_names(entries: list[GoogleDriveFileToDownload]) -> dict[str, str]:
    """Map each entry's Drive file ID to a local file name, prefixing every file whose name isn't unique."""
    name_counts = Counter(entry.path for entry in entries)
    return {
        entry.id: f"{entry.id}_{entry.path}" if name_counts[entry.path] > 1 else entry.path for entry in entries
    }


def list_drive_folder_files(folder_url: str, output_dir: Path) -> list[GoogleDriveFileToDownload]:
    try:
        entries = gdown.download_folder(url=folder_url, output=str(output_dir), skip_download=True, use_cookies=False)
    except gdown.exceptions.DownloadError as error:
        raise DriveDownloadError(f"Could not list folder {folder_url!r}: {error}") from error
    return cast("list[GoogleDriveFileToDownload]", entries)


def download_drive_folder(folder_url: str, output_dir: Path) -> list[Path]:
    """Download every file in a public Google Drive folder into output_dir, skipping files already there.

    A file whose name collides with a different Drive file's name is saved with its Drive file ID
    prefixed, so a collision never silently drops or overwrites a photo.
    """
    with log_call(logger, "download_drive_folder", folder_url=folder_url, output_dir=str(output_dir)):
        entries = list_drive_folder_files(folder_url, output_dir)
        local_file_names = build_collision_safe_file_names(entries)
        downloaded_file_paths: list[Path] = []
        for entry in entries:
            local_path = output_dir / local_file_names[entry.id]
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                gdown.download(id=entry.id, output=str(local_path), quiet=False, use_cookies=False, resume=True)
            except gdown.exceptions.DownloadError as error:
                raise DriveDownloadError(f"Could not download file {entry.id!r} ({entry.path!r}): {error}") from error
            downloaded_file_paths.append(local_path)
        return downloaded_file_paths
