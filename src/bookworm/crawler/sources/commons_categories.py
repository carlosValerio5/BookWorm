import re
import tomllib
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit

from selectolax.parser import HTMLParser

from bookworm.crawler.crawl_types import CrawlRequest, CrawlSource, ExtractionError, FetchedResponse, RequestPurpose
from bookworm.crawler.file_saving import FILE_SUFFIX_BY_MEDIA_TYPE
from bookworm.crawler.html_extraction import extract_link_urls

SOURCE_NAME = "commons_categories"
COMMONS_URL = "https://commons.wikimedia.org"
COMMONS_MIN_SECONDS_BETWEEN_REQUESTS = 2.0
MIN_IMAGE_LONG_SIDE = 640
PHOTO_FILE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
PIXEL_COUNT = re.compile(r"\d[\d,]*")


def build_category_url(category_name: str) -> str:
    return f"{COMMONS_URL}/wiki/Category:{category_name.replace(' ', '_')}"


def build_seed_requests(seed_file: Path) -> list[CrawlRequest]:
    categories = tomllib.loads(seed_file.read_text())["categories"]
    return [
        CrawlRequest(
            url=build_category_url(category["name"]),
            source_name=SOURCE_NAME,
            purpose=RequestPurpose.PARSE,
            depth=0,
            labels={"expected_content": category["expected_content"], "category": category["name"]},
        )
        for category in categories
    ]


def extract_requests(response: FetchedResponse) -> list[CrawlRequest]:
    page_kind = read_page_kind(response.request.url)
    return EXTRACTOR_BY_PAGE_KIND.get(page_kind, reject_unknown_page)(response)


def read_page_kind(page_url: str) -> str:
    page_title = unquote(urlsplit(page_url).path).removeprefix("/wiki/")
    return page_title.partition(":")[0]


def reject_unknown_page(response: FetchedResponse) -> list[CrawlRequest]:
    raise ExtractionError(f"Commons page at {response.request.url} is neither a category nor a file page")


def extract_from_category_page(response: FetchedResponse) -> list[CrawlRequest]:
    media_section = HTMLParser(response.body.decode("utf-8", errors="replace")).css_first("#mw-category-media")
    media_html = (media_section.html or "") if media_section else ""
    photo_page_urls = [url for url in extract_link_urls(response.request.url, media_html) if is_photo_file_page(url)]
    return [
        CrawlRequest(
            url=photo_page_url,
            source_name=SOURCE_NAME,
            purpose=RequestPurpose.PARSE,
            depth=response.request.depth + 1,
            labels=dict(response.request.labels),
        )
        for photo_page_url in photo_page_urls
    ]


def is_photo_file_page(url: str) -> bool:
    page_path = unquote(urlsplit(url).path)
    return page_path.startswith("/wiki/File:") and PurePosixPath(page_path).suffix.lower() in PHOTO_FILE_EXTENSIONS


def extract_from_file_page(response: FetchedResponse) -> list[CrawlRequest]:
    tree = HTMLParser(response.body.decode("utf-8", errors="replace"))
    image_href = select_largest_thumbnail_href(tree) or read_original_href(tree, response.request.url)
    return [
        CrawlRequest(
            url=remove_query(urljoin(response.request.url, image_href)),
            source_name=SOURCE_NAME,
            purpose=RequestPurpose.DOWNLOAD,
            depth=response.request.depth + 1,
            labels={**response.request.labels, "file_page_url": response.request.url, "license": read_license(tree)},
        )
    ]


def select_largest_thumbnail_href(tree: HTMLParser) -> str:
    thumbnails = [
        (read_long_side(link.text()), link.attributes.get("href") or "")
        for link in tree.css(".mw-filepage-other-resolutions a.mw-thumbnail-link")
    ]
    large_thumbnails = [thumbnail for thumbnail in thumbnails if thumbnail[0] >= MIN_IMAGE_LONG_SIDE]
    _, largest_href = max(large_thumbnails, default=(0, ""))
    return largest_href


def read_long_side(size_text: str) -> int:
    return max((int(pixel_count.replace(",", "")) for pixel_count in PIXEL_COUNT.findall(size_text)), default=0)


def read_original_href(tree: HTMLParser, page_url: str) -> str:
    original_link = tree.css_first(".fullMedia a")
    if original_link is None:
        raise ExtractionError(f"Commons file page at {page_url} has no original image link")
    return original_link.attributes.get("href") or ""


def read_license(tree: HTMLParser) -> str:
    license_node = tree.css_first(".licensetpl_short")
    return license_node.text().strip() if license_node else ""


def remove_query(url: str) -> str:
    return urlsplit(url)._replace(query="", fragment="").geturl()


EXTRACTOR_BY_PAGE_KIND: dict[str, Callable[[FetchedResponse], list[CrawlRequest]]] = {
    "Category": extract_from_category_page,
    "File": extract_from_file_page,
}

COMMONS_CATEGORIES_SOURCE = CrawlSource(
    name=SOURCE_NAME,
    min_seconds_between_requests=COMMONS_MIN_SECONDS_BETWEEN_REQUESTS,
    max_depth=1,
    min_image_long_side=MIN_IMAGE_LONG_SIDE,
    accepted_image_media_types=frozenset(FILE_SUFFIX_BY_MEDIA_TYPE),
    build_seed_requests=build_seed_requests,
    extract_requests=extract_requests,
)
