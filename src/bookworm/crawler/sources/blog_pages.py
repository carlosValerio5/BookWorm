import re
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from bookworm.crawler.crawl_types import CrawlRequest, CrawlSource, FetchedResponse, RequestPurpose
from bookworm.crawler.file_saving import FILE_SUFFIX_BY_MEDIA_TYPE
from bookworm.crawler.html_extraction import extract_image_urls, extract_link_urls

SOURCE_NAME = "blog_pages"
BLOG_MIN_SECONDS_BETWEEN_REQUESTS = 2.0
MIN_IMAGE_LONG_SIDE = 600
BLOCKED_IMAGE_HOST_SUFFIXES = ("pixel.wp.com", "gravatar.com", "cdninstagram.com", "netgalley.com")
SPINE_IMAGE_URL = re.compile(r"spine", re.IGNORECASE)


def build_seed_requests(seed_file: Path) -> list[CrawlRequest]:
    pages = tomllib.loads(seed_file.read_text())["pages"]
    return [
        CrawlRequest(
            url=page["url"],
            source_name=SOURCE_NAME,
            purpose=RequestPurpose.PARSE,
            depth=0,
            labels={
                "expected_content": page["expected_content"],
                "seed_url": page["url"],
                "follow_link_pattern": page["follow_link_pattern"],
            },
        )
        for page in pages
    ]


def extract_requests(response: FetchedResponse) -> list[CrawlRequest]:
    html = response.body.decode("utf-8", errors="replace")
    return build_image_download_requests(response.request, html) + build_follow_link_requests(response.request, html)


def build_image_download_requests(page_request: CrawlRequest, html: str) -> list[CrawlRequest]:
    image_urls = [url for url in extract_image_urls(page_request.url, html) if not is_blocked_image_host(url)]
    return [
        CrawlRequest(
            url=image_url,
            source_name=SOURCE_NAME,
            purpose=RequestPurpose.DOWNLOAD,
            depth=page_request.depth + 1,
            labels=build_image_labels(page_request, image_url),
        )
        for image_url in image_urls
    ]


def build_image_labels(page_request: CrawlRequest, image_url: str) -> dict[str, str]:
    expected_content = "spine" if SPINE_IMAGE_URL.search(image_url) else page_request.labels["expected_content"]
    return {**page_request.labels, "page_url": page_request.url, "expected_content": expected_content}


def is_blocked_image_host(image_url: str) -> bool:
    return (urlsplit(image_url).hostname or "").endswith(BLOCKED_IMAGE_HOST_SUFFIXES)


def build_follow_link_requests(page_request: CrawlRequest, html: str) -> list[CrawlRequest]:
    page_host = urlsplit(page_request.url).hostname
    follow_link_pattern = re.compile(page_request.labels["follow_link_pattern"])
    link_urls = [
        url
        for url in extract_link_urls(page_request.url, html)
        if urlsplit(url).hostname == page_host and follow_link_pattern.search(url)
    ]
    return [
        CrawlRequest(
            url=link_url,
            source_name=SOURCE_NAME,
            purpose=RequestPurpose.PARSE,
            depth=page_request.depth + 1,
            labels=dict(page_request.labels),
        )
        for link_url in link_urls
    ]


BLOG_PAGES_SOURCE = CrawlSource(
    name=SOURCE_NAME,
    min_seconds_between_requests=BLOG_MIN_SECONDS_BETWEEN_REQUESTS,
    max_depth=1,
    min_image_long_side=MIN_IMAGE_LONG_SIDE,
    accepted_image_media_types=frozenset(FILE_SUFFIX_BY_MEDIA_TYPE),
    build_seed_requests=build_seed_requests,
    extract_requests=extract_requests,
)
