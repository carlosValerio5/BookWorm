from pathlib import Path

import pytest
from crawler_factories import create_crawl_request, create_fetched_response, create_openverse_page_body, create_openverse_result

from bookworm.crawler.crawl_types import CrawlRequest, ExtractionError, RequestPurpose
from bookworm.crawler.sources.openverse_photos import OPENVERSE_PHOTOS_SOURCE, build_openverse_search_url

QUERY_LABELS = {"query": "thrift books", "expected_content": "cover"}


def create_search_page_request(page: int = 1) -> CrawlRequest:
    return create_crawl_request(
        url=build_openverse_search_url("thrift books", page),
        source_name=OPENVERSE_PHOTOS_SOURCE.name,
        labels=QUERY_LABELS,
    )


def extract_from_page(results: list[dict], page: int = 1, page_count: int = 1) -> list[CrawlRequest]:
    request = create_search_page_request(page)
    body = create_openverse_page_body(results, page=page, page_count=page_count)
    return OPENVERSE_PHOTOS_SOURCE.extract_requests(create_fetched_response(request, body, "application/json"))


def test_search_url_is_stable() -> None:
    assert build_openverse_search_url("thrift books", 2) == (
        "https://api.openverse.org/v1/images/?q=thrift+books&page=2&page_size=20"
    )


def test_seed_requests_search_the_first_page_of_each_query(tmp_path: Path) -> None:
    seed_file = tmp_path / "queries.toml"
    seed_file.write_text(
        '[[queries]]\ntext = "thrift books"\nexpected_content = "cover"\n\n'
        '[[queries]]\ntext = "isbn"\nexpected_content = "isbn"\n'
    )

    seed_requests = OPENVERSE_PHOTOS_SOURCE.build_seed_requests(seed_file)

    assert [(request.url, request.purpose, request.depth, request.labels) for request in seed_requests] == [
        (build_openverse_search_url("thrift books", 1), RequestPurpose.PARSE, 0, QUERY_LABELS),
        (build_openverse_search_url("isbn", 1), RequestPurpose.PARSE, 0, {"query": "isbn", "expected_content": "isbn"}),
    ]


def test_extract_creates_a_download_per_result_with_license_labels() -> None:
    [download_request] = extract_from_page([create_openverse_result("https://live.staticflickr.com/1/a_b.jpg")])

    assert download_request.url == "https://live.staticflickr.com/1/a_b.jpg"
    assert download_request.purpose == RequestPurpose.DOWNLOAD
    assert download_request.depth == 1
    assert download_request.labels == {
        **QUERY_LABELS,
        "openverse_id": "result-a_b.jpg",
        "title": "Thrift Books",
        "creator": "someone",
        "license": "by",
        "license_version": "2.0",
        "provider": "flickr",
        "landing_url": "https://www.flickr.com/photos/someone/1",
    }


def test_extract_requests_the_next_page_at_the_same_depth() -> None:
    next_page_requests = extract_from_page([], page=1, page_count=12)

    assert [(request.url, request.purpose, request.depth, request.labels) for request in next_page_requests] == [
        (build_openverse_search_url("thrift books", 2), RequestPurpose.PARSE, 0, QUERY_LABELS)
    ]


def test_extract_stops_at_the_last_page() -> None:
    assert extract_from_page([], page=12, page_count=12) == []


def test_extract_skips_results_known_to_be_too_small() -> None:
    small_result = create_openverse_result("https://live.staticflickr.com/1/small.jpg", width=500, height=333)

    assert extract_from_page([small_result]) == []


def test_extract_keeps_results_with_unknown_size() -> None:
    unknown_size_result = create_openverse_result("https://live.staticflickr.com/1/unknown.jpg", width=None, height=None)

    assert [request.url for request in extract_from_page([unknown_size_result])] == [
        "https://live.staticflickr.com/1/unknown.jpg"
    ]


def test_extract_skips_mature_results() -> None:
    mature_result = create_openverse_result("https://live.staticflickr.com/1/mature.jpg", mature=True)

    assert extract_from_page([mature_result]) == []


def test_extract_raises_extraction_error_on_a_body_that_is_not_json() -> None:
    response = create_fetched_response(create_search_page_request(), b"\n<html>busy</html>", "text/html")

    with pytest.raises(ExtractionError):
        OPENVERSE_PHOTOS_SOURCE.extract_requests(response)
