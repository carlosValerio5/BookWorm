from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class RequestPurpose(StrEnum):
    PARSE = "parse"
    DOWNLOAD = "download"


class RequestStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExtractionError(Exception):
    pass


@dataclass(frozen=True)
class CrawlRequest:
    url: str
    source_name: str
    purpose: RequestPurpose
    depth: int
    labels: dict[str, str]


@dataclass(frozen=True)
class FetchedResponse:
    request: CrawlRequest
    status_code: int
    media_type: str
    body: bytes


@dataclass(frozen=True)
class SavedFile:
    content_sha256: str
    file_path: str
    source_name: str
    source_url: str
    labels: dict[str, str]


@dataclass(frozen=True)
class CrawlSource:
    name: str
    min_seconds_between_requests: float
    max_depth: int
    min_image_long_side: int
    accepted_image_media_types: frozenset[str]
    build_seed_requests: Callable[[Path], list[CrawlRequest]]
    extract_requests: Callable[[FetchedResponse], list[CrawlRequest]]
