import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path

import pytest
from crawler_factories import TEST_SOURCE_NAME, create_crawl_request, create_saved_file

from bookworm.crawler.crawl_state import (
    count_requests_by_status,
    count_saved_files_by_expected_content,
    enqueue_requests,
    find_next_pending_request,
    mark_request_done,
    mark_request_failed,
    mark_request_skipped,
    open_crawl_state,
    record_saved_file,
    reset_failed_requests,
)
from bookworm.crawler.crawl_types import RequestPurpose


@pytest.fixture
def crawl_state(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(open_crawl_state(tmp_path / "crawl_state.sqlite3")) as connection:
        yield connection


def test_enqueue_keeps_one_row_per_url(crawl_state: sqlite3.Connection) -> None:
    request = create_crawl_request(url="https://blog.example/1")

    assert enqueue_requests(crawl_state, [request, request]) == 1
    assert enqueue_requests(crawl_state, [request]) == 0


def test_next_pending_request_follows_insertion_order(crawl_state: sqlite3.Connection) -> None:
    urls = ["https://blog.example/3", "https://blog.example/1", "https://blog.example/2"]
    enqueue_requests(crawl_state, [create_crawl_request(url=url) for url in urls])

    taken_urls = []
    for _ in urls:
        request = find_next_pending_request(crawl_state, TEST_SOURCE_NAME)
        assert request is not None
        taken_urls.append(request.url)
        mark_request_done(crawl_state, request.url)

    assert taken_urls == urls


def test_next_pending_request_is_none_when_queue_is_empty(crawl_state: sqlite3.Connection) -> None:
    assert find_next_pending_request(crawl_state, TEST_SOURCE_NAME) is None


def test_next_pending_request_ignores_other_sources(crawl_state: sqlite3.Connection) -> None:
    enqueue_requests(crawl_state, [create_crawl_request(source_name="other_source")])

    assert find_next_pending_request(crawl_state, TEST_SOURCE_NAME) is None


def test_request_keeps_purpose_depth_and_labels(crawl_state: sqlite3.Connection) -> None:
    request = create_crawl_request(purpose=RequestPurpose.DOWNLOAD, depth=2, labels={"expected_content": "isbn"})
    enqueue_requests(crawl_state, [request])

    assert find_next_pending_request(crawl_state, TEST_SOURCE_NAME) == request


def test_failed_and_skipped_requests_are_no_longer_pending(crawl_state: sqlite3.Connection) -> None:
    enqueue_requests(
        crawl_state, [create_crawl_request(url="https://blog.example/1"), create_crawl_request(url="https://blog.example/2")]
    )

    mark_request_failed(crawl_state, "https://blog.example/1", "http_404")
    mark_request_skipped(crawl_state, "https://blog.example/2", "disallowed_by_robots")

    assert count_requests_by_status(crawl_state, TEST_SOURCE_NAME) == {"failed": 1, "skipped": 1}


def test_reset_failed_requests_makes_them_pending_again(crawl_state: sqlite3.Connection) -> None:
    enqueue_requests(crawl_state, [create_crawl_request(url="https://blog.example/1")])
    mark_request_failed(crawl_state, "https://blog.example/1", "http_500")

    assert reset_failed_requests(crawl_state, TEST_SOURCE_NAME) == 1
    assert count_requests_by_status(crawl_state, TEST_SOURCE_NAME) == {"pending": 1}


def test_record_saved_file_returns_false_for_content_already_saved(crawl_state: sqlite3.Connection) -> None:
    saved_file = create_saved_file()

    assert record_saved_file(crawl_state, saved_file) is True
    assert record_saved_file(crawl_state, saved_file) is False


def test_counts_saved_files_by_source_and_expected_content(crawl_state: sqlite3.Connection) -> None:
    record_saved_file(crawl_state, create_saved_file(content_sha256="a" * 64, expected_content="cover"))
    record_saved_file(crawl_state, create_saved_file(content_sha256="b" * 64, expected_content="cover"))
    record_saved_file(crawl_state, create_saved_file(content_sha256="c" * 64, expected_content="isbn"))

    assert count_saved_files_by_expected_content(crawl_state) == {
        (TEST_SOURCE_NAME, "cover"): 2,
        (TEST_SOURCE_NAME, "isbn"): 1,
    }


def test_queue_survives_reopening_the_state_file(tmp_path: Path) -> None:
    state_path = tmp_path / "crawl_state.sqlite3"
    with closing(open_crawl_state(state_path)) as first_connection:
        enqueue_requests(first_connection, [create_crawl_request(url="https://blog.example/1")])

    with closing(open_crawl_state(state_path)) as reopened_connection:
        reopened_request = find_next_pending_request(reopened_connection, TEST_SOURCE_NAME)

    assert reopened_request is not None
    assert reopened_request.url == "https://blog.example/1"
