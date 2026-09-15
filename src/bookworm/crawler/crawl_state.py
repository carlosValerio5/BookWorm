import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

import structlog

from bookworm.crawler.crawl_types import CrawlRequest, RequestPurpose, RequestStatus, SavedFile
from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS crawl_requests (
        queue_position INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL UNIQUE,
        source_name TEXT NOT NULL,
        purpose TEXT NOT NULL,
        depth INTEGER NOT NULL,
        labels_json TEXT NOT NULL,
        status TEXT NOT NULL,
        status_reason TEXT,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS saved_files (
        content_sha256 TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        source_name TEXT NOT NULL,
        source_url TEXT NOT NULL,
        labels_json TEXT NOT NULL,
        saved_at TEXT NOT NULL
    )
    """,
)


def open_crawl_state(state_path: Path) -> sqlite3.Connection:
    with log_call(logger, "open_crawl_state", state_path=str(state_path)):
        state_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(state_path, autocommit=True)
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
    return connection


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def enqueue_requests(connection: sqlite3.Connection, requests: Iterable[CrawlRequest]) -> int:
    rows = [
        (
            request.url,
            request.source_name,
            str(request.purpose),
            request.depth,
            json.dumps(request.labels, sort_keys=True),
            str(RequestStatus.PENDING),
            utc_now_iso(),
        )
        for request in requests
    ]
    changes_before = connection.total_changes
    connection.executemany(
        "INSERT OR IGNORE INTO crawl_requests (url, source_name, purpose, depth, labels_json, status, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    added_count = connection.total_changes - changes_before
    logger.info("requests_enqueued", offered_count=len(rows), added_count=added_count)
    return added_count


def find_next_pending_request(connection: sqlite3.Connection, source_name: str) -> CrawlRequest | None:
    row = connection.execute(
        "SELECT url, source_name, purpose, depth, labels_json FROM crawl_requests"
        " WHERE source_name = ? AND status = ? ORDER BY queue_position LIMIT 1",
        (source_name, str(RequestStatus.PENDING)),
    ).fetchone()
    return None if row is None else build_request_from_row(row)


def build_request_from_row(row: tuple[str, str, str, int, str]) -> CrawlRequest:
    url, source_name, purpose, depth, labels_json = row
    return CrawlRequest(
        url=url,
        source_name=source_name,
        purpose=RequestPurpose(purpose),
        depth=depth,
        labels=json.loads(labels_json),
    )


def update_request_status(connection: sqlite3.Connection, url: str, status: RequestStatus, reason: str | None) -> None:
    connection.execute(
        "UPDATE crawl_requests SET status = ?, status_reason = ?, updated_at = ? WHERE url = ?",
        (str(status), reason, utc_now_iso(), url),
    )
    logger.info("request_status_changed", url=url, status=str(status), status_reason=reason)


def mark_request_done(connection: sqlite3.Connection, url: str) -> None:
    update_request_status(connection, url, RequestStatus.DONE, None)


def mark_request_failed(connection: sqlite3.Connection, url: str, reason: str) -> None:
    update_request_status(connection, url, RequestStatus.FAILED, reason)


def mark_request_skipped(connection: sqlite3.Connection, url: str, reason: str) -> None:
    update_request_status(connection, url, RequestStatus.SKIPPED, reason)


def reset_failed_requests(connection: sqlite3.Connection, source_name: str) -> int:
    cursor = connection.execute(
        "UPDATE crawl_requests SET status = ?, status_reason = NULL, updated_at = ? WHERE source_name = ? AND status = ?",
        (str(RequestStatus.PENDING), utc_now_iso(), source_name, str(RequestStatus.FAILED)),
    )
    logger.info("failed_requests_reset", reset_count=cursor.rowcount)
    return cursor.rowcount


def record_saved_file(connection: sqlite3.Connection, saved_file: SavedFile) -> bool:
    cursor = connection.execute(
        "INSERT OR IGNORE INTO saved_files (content_sha256, file_path, source_name, source_url, labels_json, saved_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (
            saved_file.content_sha256,
            saved_file.file_path,
            saved_file.source_name,
            saved_file.source_url,
            json.dumps(saved_file.labels, sort_keys=True),
            utc_now_iso(),
        ),
    )
    return cursor.rowcount == 1


def list_source_names(connection: sqlite3.Connection) -> list[str]:
    rows = connection.execute("SELECT DISTINCT source_name FROM crawl_requests ORDER BY source_name").fetchall()
    return [source_name for (source_name,) in rows]


def count_requests_by_status(connection: sqlite3.Connection, source_name: str) -> dict[str, int]:
    rows = connection.execute(
        "SELECT status, COUNT(*) FROM crawl_requests WHERE source_name = ? GROUP BY status ORDER BY status",
        (source_name,),
    ).fetchall()
    return dict(rows)


def count_saved_files_by_expected_content(connection: sqlite3.Connection) -> dict[tuple[str, str], int]:
    rows = connection.execute(
        "SELECT source_name, json_extract(labels_json, '$.expected_content'), COUNT(*) FROM saved_files"
        " GROUP BY 1, 2 ORDER BY 1, 2"
    ).fetchall()
    return {(source_name, expected_content): count for source_name, expected_content, count in rows}
