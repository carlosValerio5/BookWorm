import sqlite3
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import structlog

from bookworm.crawler.crawl_state import (
    enqueue_requests,
    find_next_pending_request,
    mark_request_done,
    mark_request_failed,
    mark_request_skipped,
    record_saved_file,
)
from bookworm.crawler.crawl_types import CrawlRequest, CrawlSource, ExtractionError, FetchedResponse, RequestPurpose
from bookworm.crawler.file_saving import build_saved_file, write_file_body
from bookworm.crawler.http_fetching import FetchError, fetch_request
from bookworm.crawler.image_size_reading import ImageDecodeError, read_image_long_side
from bookworm.crawler.request_pacing import HostPacer
from bookworm.crawler.robots_policy import RobotsPolicy
from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

RATE_LIMIT_STATUS_CODES = frozenset({429})
MAX_IMAGE_LONG_SIDE = 16384


class StopReason(StrEnum):
    QUEUE_EMPTY = "queue_empty"
    BUDGET_REACHED = "budget_reached"
    RATE_LIMITED = "rate_limited"


class RequestSkipped(Exception):
    pass


class RequestFailed(Exception):
    pass


class RequestRedirected(Exception):
    pass


class RateLimited(Exception):
    pass


FAILURE_ERRORS = (RequestFailed, FetchError, ExtractionError, ImageDecodeError)


@dataclass(frozen=True)
class CrawlContext:
    source: CrawlSource
    connection: sqlite3.Connection
    client: httpx.Client
    robots_policy: RobotsPolicy
    pacer: HostPacer
    dataset_dir: Path


@dataclass(frozen=True)
class CrawlRunSummary:
    requests_handled: int
    files_saved: int
    stop_reason: StopReason


def run_crawl(context: CrawlContext, max_requests: int) -> CrawlRunSummary:
    run_fields = {"crawl_run_id": uuid.uuid4().hex, "source_name": context.source.name}
    with structlog.contextvars.bound_contextvars(**run_fields), log_call(logger, "run_crawl", max_requests=max_requests):
        summary = crawl_until_stopped(context, max_requests)
        logger.info(
            "crawl_run_stopped",
            requests_handled=summary.requests_handled,
            files_saved=summary.files_saved,
            stop_reason=str(summary.stop_reason),
        )
    return summary


def crawl_until_stopped(context: CrawlContext, max_requests: int) -> CrawlRunSummary:
    requests_handled = 0
    files_saved = 0
    while requests_handled < max_requests:
        request = find_next_pending_request(context.connection, context.source.name)
        if request is None:
            return CrawlRunSummary(requests_handled, files_saved, StopReason.QUEUE_EMPTY)
        try:
            files_saved += handle_request(context, request)
        except RateLimited as rate_limit:
            logger.warning("rate_limited_run_stopped", url=request.url, status_reason=str(rate_limit))
            return CrawlRunSummary(requests_handled, files_saved, StopReason.RATE_LIMITED)
        requests_handled += 1
    return CrawlRunSummary(requests_handled, files_saved, StopReason.BUDGET_REACHED)


def handle_request(context: CrawlContext, request: CrawlRequest) -> int:
    try:
        saved_file_count = process_request(context, request)
    except RequestSkipped as skip:
        mark_request_skipped(context.connection, request.url, str(skip))
        return 0
    except RequestRedirected as redirect:
        follow_redirect(context, request, str(redirect))
        return 0
    except FAILURE_ERRORS as failure:
        mark_request_failed(context.connection, request.url, f"{type(failure).__name__}: {failure}")
        return 0
    mark_request_done(context.connection, request.url)
    return saved_file_count


def follow_redirect(context: CrawlContext, request: CrawlRequest, redirect_url: str) -> None:
    enqueue_requests(context.connection, [replace(request, url=redirect_url)])
    mark_request_skipped(context.connection, request.url, f"redirected_to:{redirect_url}")


def process_request(context: CrawlContext, request: CrawlRequest) -> int:
    ensure_allowed_by_robots(context.robots_policy, request)
    context.pacer.wait_for_host(urlsplit(request.url).netloc)
    response = fetch_request(context.client, request)
    ensure_not_rate_limited(response)
    ensure_not_redirected(response)
    ensure_success_status(response)
    return RESPONSE_HANDLER_BY_PURPOSE[request.purpose](context, response)


def ensure_allowed_by_robots(robots_policy: RobotsPolicy, request: CrawlRequest) -> None:
    if not robots_policy.is_url_allowed(request.url):
        raise RequestSkipped("disallowed_by_robots")


def ensure_not_rate_limited(response: FetchedResponse) -> None:
    if response.status_code in RATE_LIMIT_STATUS_CODES:
        raise RateLimited(f"http_{response.status_code}")


def ensure_not_redirected(response: FetchedResponse) -> None:
    if response.redirect_url:
        raise RequestRedirected(response.redirect_url)


def ensure_success_status(response: FetchedResponse) -> None:
    if response.status_code // 100 != 2:
        raise RequestFailed(f"http_{response.status_code}")


def handle_parse_response(context: CrawlContext, response: FetchedResponse) -> int:
    extracted_requests = context.source.extract_requests(response)
    requests_within_depth = [request for request in extracted_requests if is_within_max_depth(context.source, request)]
    added_count = enqueue_requests(context.connection, requests_within_depth)
    logger.info(
        "page_parsed",
        url=response.request.url,
        extracted_count=len(extracted_requests),
        within_depth_count=len(requests_within_depth),
        added_count=added_count,
    )
    return 0


def is_within_max_depth(source: CrawlSource, request: CrawlRequest) -> bool:
    return request.purpose == RequestPurpose.DOWNLOAD or request.depth <= source.max_depth


def handle_download_response(context: CrawlContext, response: FetchedResponse) -> int:
    ensure_accepted_image_media_type(context.source, response)
    ensure_image_long_side_within_limits(context.source, response)
    saved_file = build_saved_file(context.dataset_dir, response)
    write_file_body(saved_file, response.body)
    is_new_file = record_saved_file(context.connection, saved_file)
    logger.info("file_saved", url=response.request.url, content_sha256=saved_file.content_sha256, is_new_file=is_new_file)
    return int(is_new_file)


def ensure_accepted_image_media_type(source: CrawlSource, response: FetchedResponse) -> None:
    if response.media_type not in source.accepted_image_media_types:
        raise RequestFailed(f"unaccepted_media_type:{response.media_type}")


def ensure_image_long_side_within_limits(source: CrawlSource, response: FetchedResponse) -> None:
    image_long_side = read_image_long_side(response.body)
    if image_long_side < source.min_image_long_side:
        raise RequestSkipped(f"image_too_small:{image_long_side}px")
    if image_long_side > MAX_IMAGE_LONG_SIDE:
        raise RequestSkipped(f"image_too_large:{image_long_side}px")


RESPONSE_HANDLER_BY_PURPOSE: dict[RequestPurpose, Callable[[CrawlContext, FetchedResponse], int]] = {
    RequestPurpose.PARSE: handle_parse_response,
    RequestPurpose.DOWNLOAD: handle_download_response,
}
