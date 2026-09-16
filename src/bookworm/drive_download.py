from pathlib import Path
from typing import cast

import gdown
import gdown.exceptions
import structlog

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)


class DriveDownloadError(Exception):
    pass


def download_drive_folder(folder_url: str, output_dir: Path) -> list[Path]:
    """Download every file in a public Google Drive folder into output_dir, skipping files already there."""
    with log_call(logger, "download_drive_folder", folder_url=folder_url, output_dir=str(output_dir)):
        try:
            downloaded_file_paths = gdown.download_folder(
                url=folder_url,
                output=str(output_dir),
                quiet=False,
                use_cookies=False,
                resume=True,
            )
        except gdown.exceptions.DownloadError as error:
            raise DriveDownloadError(f"Could not download folder {folder_url!r}: {error}") from error
        return [Path(file_path) for file_path in cast("list[str]", downloaded_file_paths)]
