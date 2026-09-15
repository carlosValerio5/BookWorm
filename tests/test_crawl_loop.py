import hashlib
import json
from pathlib import Path

from crawler_factories import MISSING_ROBOTS_ROUTE, MockRoute, build_mock_client, create_crawl_request, create_encoded_image

from bookworm.crawler.crawl_loop import CrawlContext, StopReason, run_crawl
from bookworm.crawler.crawl_state import (
    count_requests_by_status,
    count_saved_files_by_expected_content,
    enqueue_requests,
    open_crawl_state,
)
from bookworm.crawler.crawl_types import CrawlRequest, CrawlSource, ExtractionError, FetchedResponse, RequestPurpose
from bookworm.crawler.request_pacing import HostPacer
from bookworm.crawler.robots_policy import RobotsPolicy
from bookworm.logging_setup import configure_logging

FAKE_SOURCE_NAME = "fake_blog"
SEED_URL = "https://blog.example/haul"
IMAGE_URL = "https://img.example/haul.jpg"
LARGE_IMAGE = create_encoded_image(width=128, height=96)
ROUTES_WITHOUT_ROBOTS = {
    "https://blog.example/robots.txt": MISSING_ROBOTS_ROUTE,
    "https://img.example/robots.txt": MISSING_ROBOTS_ROUTE,
}


def build_fake_request(line: str, parent_request: CrawlRequest) -> CrawlRequest:
    purpose_value, _, url = line.partition(" ")
    try:
        purpose = RequestPurpose(purpose_value)
    except ValueError as error:
        raise ExtractionError(f"Unknown fake page line {line!r}") from error
    return CrawlRequest(
        url=url,
        source_name=FAKE_SOURCE_NAME,
        purpose=purpose,
        depth=parent_request.depth + 1,
        labels=dict(parent_request.labels),
    )


def extract_fake_requests(response: FetchedResponse) -> list[CrawlRequest]:
    return [build_fake_request(line, response.request) for line in response.body.decode().splitlines()]


FAKE_SOURCE = CrawlSource(
    name=FAKE_SOURCE_NAME,
    min_seconds_between_requests=0.0,
    max_depth=1,
    min_image_long_side=64,
    accepted_image_media_types=frozenset({"image/jpeg"}),
    build_seed_requests=lambda seed_file: [],
    extract_requests=extract_fake_requests,
)


def page_route(*lines: str) -> MockRoute:
    return (200, "text/plain", "\n".join(lines).encode())


def image_route(image_bytes: bytes = LARGE_IMAGE) -> MockRoute:
    return (200, "image/jpeg", image_bytes)


def build_context(
    tmp_path: Path,
    routes_by_url: dict[str, MockRoute],
    requested_urls: list[str],
    timing_out_urls: frozenset[str] = frozenset(),
) -> CrawlContext:
    client = build_mock_client({**ROUTES_WITHOUT_ROBOTS, **routes_by_url}, requested_urls, timing_out_urls)
    return CrawlContext(
        source=FAKE_SOURCE,
        connection=open_crawl_state(tmp_path / "crawl_state.sqlite3"),
        client=client,
        robots_policy=RobotsPolicy(client),
        pacer=HostPacer(min_seconds_between_requests=0.0),
        dataset_dir=tmp_path / "crawled",
    )


def enqueue_seed_page(context: CrawlContext) -> None:
    seed_request = create_crawl_request(url=SEED_URL, source_name=FAKE_SOURCE_NAME, labels={"expected_content": "cover"})
    enqueue_requests(context.connection, [seed_request])


def run_seeded_crawl(tmp_path: Path, routes_by_url: dict[str, MockRoute], max_requests: int = 10) -> CrawlContext:
    context = build_context(tmp_path, routes_by_url, [])
    enqueue_seed_page(context)
    run_crawl(context, max_requests=max_requests)
    return context


def test_parse_then_download_saves_the_image_with_its_labels(tmp_path: Path) -> None:
    context = build_context(tmp_path, {SEED_URL: page_route(f"download {IMAGE_URL}"), IMAGE_URL: image_route()}, [])
    enqueue_seed_page(context)

    summary = run_crawl(context, max_requests=10)

    assert (summary.requests_handled, summary.files_saved, summary.stop_reason) == (2, 1, StopReason.QUEUE_EMPTY)
    assert count_saved_files_by_expected_content(context.connection) == {(FAKE_SOURCE_NAME, "cover"): 1}


def test_saved_image_is_named_by_its_content_hash(tmp_path: Path) -> None:
    run_seeded_crawl(tmp_path, {SEED_URL: page_route(f"download {IMAGE_URL}"), IMAGE_URL: image_route()})

    saved_image_path = tmp_path / "crawled" / FAKE_SOURCE_NAME / f"{hashlib.sha256(LARGE_IMAGE).hexdigest()}.jpg"
    assert saved_image_path.read_bytes() == LARGE_IMAGE


def test_second_run_fetches_nothing_already_done(tmp_path: Path) -> None:
    requested_urls: list[str] = []
    routes_by_url = {SEED_URL: page_route(f"download {IMAGE_URL}"), IMAGE_URL: image_route()}
    first_context = build_context(tmp_path, routes_by_url, requested_urls)
    enqueue_seed_page(first_context)
    run_crawl(first_context, max_requests=10)
    urls_fetched_by_first_run = list(requested_urls)

    second_context = build_context(tmp_path, routes_by_url, requested_urls)
    enqueue_seed_page(second_context)
    summary = run_crawl(second_context, max_requests=10)

    assert summary.stop_reason == StopReason.QUEUE_EMPTY
    assert requested_urls == urls_fetched_by_first_run


def test_run_stops_when_the_request_budget_is_reached(tmp_path: Path) -> None:
    routes_by_url = {
        SEED_URL: page_route("download https://img.example/1.jpg", "download https://img.example/2.jpg"),
        "https://img.example/1.jpg": image_route(),
        "https://img.example/2.jpg": image_route(),
    }
    context = build_context(tmp_path, routes_by_url, [])
    enqueue_seed_page(context)

    summary = run_crawl(context, max_requests=2)

    assert (summary.requests_handled, summary.stop_reason) == (2, StopReason.BUDGET_REACHED)
    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 2, "pending": 1}


def test_rate_limited_response_stops_the_run_and_keeps_the_request_pending(tmp_path: Path) -> None:
    context = build_context(
        tmp_path, {SEED_URL: page_route(f"download {IMAGE_URL}"), IMAGE_URL: (429, "text/plain", b"slow down")}, []
    )
    enqueue_seed_page(context)

    summary = run_crawl(context, max_requests=10)

    assert summary.stop_reason == StopReason.RATE_LIMITED
    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 1, "pending": 1}


def test_request_disallowed_by_robots_is_skipped_without_fetching(tmp_path: Path) -> None:
    requested_urls: list[str] = []
    routes_by_url = {
        SEED_URL: page_route(f"download {IMAGE_URL}"),
        "https://img.example/robots.txt": (200, "text/plain", b"User-agent: *\nDisallow: /\n"),
        IMAGE_URL: image_route(),
    }
    context = build_context(tmp_path, routes_by_url, requested_urls)
    enqueue_seed_page(context)

    run_crawl(context, max_requests=10)

    assert IMAGE_URL not in requested_urls
    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 1, "skipped": 1}


def test_image_smaller_than_the_minimum_is_skipped(tmp_path: Path) -> None:
    small_image_route = image_route(create_encoded_image(width=32, height=32))
    context = run_seeded_crawl(tmp_path, {SEED_URL: page_route(f"download {IMAGE_URL}"), IMAGE_URL: small_image_route})

    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 1, "skipped": 1}
    assert count_saved_files_by_expected_content(context.connection) == {}


def test_not_found_response_marks_the_request_failed(tmp_path: Path) -> None:
    context = run_seeded_crawl(tmp_path, {SEED_URL: page_route(f"download {IMAGE_URL}")})

    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 1, "failed": 1}


def test_download_with_an_unaccepted_media_type_is_failed(tmp_path: Path) -> None:
    html_route = (200, "text/html", b"<html>not an image</html>")
    context = run_seeded_crawl(tmp_path, {SEED_URL: page_route(f"download {IMAGE_URL}"), IMAGE_URL: html_route})

    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 1, "failed": 1}


def test_same_image_at_two_urls_is_saved_once(tmp_path: Path) -> None:
    routes_by_url = {
        SEED_URL: page_route("download https://img.example/1.jpg", "download https://img.example/copy.jpg"),
        "https://img.example/1.jpg": image_route(),
        "https://img.example/copy.jpg": image_route(),
    }
    context = build_context(tmp_path, routes_by_url, [])
    enqueue_seed_page(context)

    summary = run_crawl(context, max_requests=10)

    assert summary.files_saved == 1
    assert len(list((tmp_path / "crawled" / FAKE_SOURCE_NAME).iterdir())) == 1
    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 3}


def test_parse_requests_deeper_than_max_depth_are_not_queued(tmp_path: Path) -> None:
    requested_urls: list[str] = []
    routes_by_url = {
        SEED_URL: page_route("parse https://blog.example/depth-1"),
        "https://blog.example/depth-1": page_route("parse https://blog.example/depth-2"),
    }
    context = build_context(tmp_path, routes_by_url, requested_urls)
    enqueue_seed_page(context)

    run_crawl(context, max_requests=10)

    assert "https://blog.example/depth-2" not in requested_urls
    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 2}


def test_timeout_marks_the_request_failed(tmp_path: Path) -> None:
    context = build_context(
        tmp_path,
        {SEED_URL: page_route(f"download {IMAGE_URL}")},
        [],
        timing_out_urls=frozenset({IMAGE_URL}),
    )
    enqueue_seed_page(context)

    run_crawl(context, max_requests=10)

    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"done": 1, "failed": 1}


def test_extraction_error_marks_the_request_failed(tmp_path: Path) -> None:
    context = run_seeded_crawl(tmp_path, {SEED_URL: page_route("this line is not a request")})

    assert count_requests_by_status(context.connection, FAKE_SOURCE_NAME) == {"failed": 1}


def test_fetch_events_carry_crawl_run_id_source_and_url(tmp_path: Path) -> None:
    log_file_path = tmp_path / "crawl.jsonl"
    configure_logging(log_file_path)

    run_seeded_crawl(tmp_path, {SEED_URL: page_route(f"download {IMAGE_URL}"), IMAGE_URL: image_route()})

    log_events = [json.loads(line) for line in log_file_path.read_text().splitlines()]
    fetch_events = [event for event in log_events if event.get("call") == "fetch_request" and event["event"] == "call_finished"]
    assert [event["url"] for event in fetch_events] == [SEED_URL, IMAGE_URL]
    assert {event["source_name"] for event in fetch_events} == {FAKE_SOURCE_NAME}
    assert len({event["crawl_run_id"] for event in fetch_events}) == 1
