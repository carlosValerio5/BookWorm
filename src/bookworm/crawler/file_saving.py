import hashlib
from pathlib import Path

import structlog

from bookworm.crawler.crawl_types import FetchedResponse, SavedFile
from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

FILE_SUFFIX_BY_MEDIA_TYPE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


def build_saved_file(dataset_dir: Path, response: FetchedResponse) -> SavedFile:
    content_sha256 = hashlib.sha256(response.body).hexdigest()
    file_name = f"{content_sha256}{FILE_SUFFIX_BY_MEDIA_TYPE[response.media_type]}"
    return SavedFile(
        content_sha256=content_sha256,
        file_path=str(dataset_dir / response.request.source_name / file_name),
        source_name=response.request.source_name,
        source_url=response.request.url,
        labels=response.request.labels,
    )


def write_file_body(saved_file: SavedFile, body: bytes) -> None:
    with log_call(logger, "write_file_body", file_path=saved_file.file_path, body_bytes=len(body)):
        file_path = Path(saved_file.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(body)
