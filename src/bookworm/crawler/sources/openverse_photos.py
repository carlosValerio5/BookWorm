import json
import tomllib
from pathlib import Path
from urllib.parse import urlencode

from bookworm.crawler.crawl_types import CrawlRequest, CrawlSource, ExtractionError, FetchedResponse, RequestPurpose
from bookworm.crawler.file_saving import FILE_SUFFIX_BY_MEDIA_TYPE

SOURCE_NAME = "openverse_photos"
OPENVERSE_SEARCH_URL = "https://api.openverse.org/v1/images/"
OPENVERSE_PAGE_SIZE = 20
OPENVERSE_MIN_SECONDS_BETWEEN_REQUESTS = 3.5
MIN_IMAGE_LONG_SIDE = 640
LABEL_NAME_BY_RESULT_FIELD = {
    "id": "openverse_id",
    "title": "title",
    "creator": "creator",
    "license": "license",
    "license_version": "license_version",
    "provider": "provider",
    "foreign_landing_url": "landing_url",
}


def build_openverse_search_url(query_text: str, page: int) -> str:
    return f"{OPENVERSE_SEARCH_URL}?{urlencode({'q': query_text, 'page': page, 'page_size': OPENVERSE_PAGE_SIZE})}"


def build_seed_requests(seed_file: Path) -> list[CrawlRequest]:
    queries = tomllib.loads(seed_file.read_text())["queries"]
    return [
        build_search_page_request({"query": query["text"], "expected_content": query["expected_content"]}, page=1, depth=0)
        for query in queries
    ]


def build_search_page_request(query_labels: dict[str, str], page: int, depth: int) -> CrawlRequest:
    return CrawlRequest(
        url=build_openverse_search_url(query_labels["query"], page),
        source_name=SOURCE_NAME,
        purpose=RequestPurpose.PARSE,
        depth=depth,
        labels=query_labels,
    )


def extract_requests(response: FetchedResponse) -> list[CrawlRequest]:
    results, page, page_count = read_search_page(response)
    download_requests = [
        build_download_request(response.request, result) for result in results if is_result_worth_downloading(result)
    ]
    return download_requests + build_next_page_requests(response.request, page, page_count)


def read_search_page(response: FetchedResponse) -> tuple[list[dict], int, int]:
    try:
        search_page = json.loads(response.body)
        return search_page["results"], search_page["page"], search_page["page_count"]
    except (ValueError, KeyError, TypeError) as error:
        raise ExtractionError(f"Openverse page at {response.request.url} is not a search result page") from error


def is_result_worth_downloading(result: dict) -> bool:
    return bool(result.get("url")) and not result.get("mature", False) and is_long_side_unknown_or_large_enough(result)


def is_long_side_unknown_or_large_enough(result: dict) -> bool:
    known_sides = [side for side in (result.get("width"), result.get("height")) if side is not None]
    return max(known_sides, default=MIN_IMAGE_LONG_SIDE) >= MIN_IMAGE_LONG_SIDE


def build_download_request(page_request: CrawlRequest, result: dict) -> CrawlRequest:
    result_labels = {label_name: str(result.get(field) or "") for field, label_name in LABEL_NAME_BY_RESULT_FIELD.items()}
    return CrawlRequest(
        url=result["url"],
        source_name=SOURCE_NAME,
        purpose=RequestPurpose.DOWNLOAD,
        depth=page_request.depth + 1,
        labels={**page_request.labels, **result_labels},
    )


def build_next_page_requests(page_request: CrawlRequest, page: int, page_count: int) -> list[CrawlRequest]:
    next_page_numbers = range(page + 1, min(page + 1, page_count) + 1)
    return [build_search_page_request(page_request.labels, next_page, page_request.depth) for next_page in next_page_numbers]


OPENVERSE_PHOTOS_SOURCE = CrawlSource(
    name=SOURCE_NAME,
    min_seconds_between_requests=OPENVERSE_MIN_SECONDS_BETWEEN_REQUESTS,
    max_depth=0,
    min_image_long_side=MIN_IMAGE_LONG_SIDE,
    accepted_image_media_types=frozenset(FILE_SUFFIX_BY_MEDIA_TYPE),
    build_seed_requests=build_seed_requests,
    extract_requests=extract_requests,
)
