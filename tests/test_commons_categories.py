from pathlib import Path

import pytest
from crawler_factories import create_crawl_request, create_fetched_response

from bookworm.crawler.crawl_types import CrawlRequest, ExtractionError, RequestPurpose
from bookworm.crawler.sources.commons_categories import COMMONS_CATEGORIES_SOURCE, build_category_url

CATEGORY_URL = "https://commons.wikimedia.org/wiki/Category:Bookshelves"
FILE_PAGE_URL = "https://commons.wikimedia.org/wiki/File:Shelf.jpg"
CATEGORY_LABELS = {"expected_content": "spine", "category": "Bookshelves"}
THUMBNAIL_BASE_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a0/Shelf.jpg"
ORIGINAL_URL = "https://upload.wikimedia.org/wikipedia/commons/a/a0/Shelf.jpg"
TRACKING_QUERY = "?utm_source=commons.wikimedia.org&utm_campaign=index&utm_content=thumbnail"


def create_category_page_html(*file_hrefs: str) -> str:
    file_links = "".join(
        f'<li class="gallerybox"><a href="{href}" class="mw-file-description"><img src="x.jpg"></a>'
        f'<a href="{href}">{href}</a></li>'
        for href in file_hrefs
    )
    return (
        '<div id="mw-subcategories"><a href="/wiki/Category:Bookshelves_by_country">by country</a></div>'
        '<div id="mw-category-media">'
        '<a href="/w/index.php?title=Category:Bookshelves&filefrom=B.jpg#mw-category-media">next page</a>'
        f'<ul class="gallery">{file_links}</ul></div>'
        '<div id="footer"><a href="/wiki/File:Wikimedia_logo.jpg">logo</a></div>'
    )


def create_file_page_html(thumbnail_links: list[tuple[str, str]], license_html: str) -> str:
    thumbnails = " | ".join(
        f'<a href="{href}" class="mw-thumbnail-link">{size_text}</a>' for size_text, href in thumbnail_links
    )
    return (
        f'<span class="mw-filepage-other-resolutions">Other resolutions: {thumbnails}</span>'
        f'<div class="fullMedia"><bdi><a href="{ORIGINAL_URL}{TRACKING_QUERY}" class="internal">Shelf.jpg</a></bdi></div>'
        f"{license_html}"
    )


def extract_from_page(page_url: str, html: str, depth: int) -> list[CrawlRequest]:
    request = create_crawl_request(
        url=page_url, source_name=COMMONS_CATEGORIES_SOURCE.name, depth=depth, labels=CATEGORY_LABELS
    )
    return COMMONS_CATEGORIES_SOURCE.extract_requests(create_fetched_response(request, html.encode()))


def summarize(requests: list[CrawlRequest]) -> list[tuple[str, RequestPurpose, int, dict[str, str]]]:
    return [(request.url, request.purpose, request.depth, request.labels) for request in requests]


def test_category_url_uses_underscores() -> None:
    assert build_category_url("Second-hand bookshops") == "https://commons.wikimedia.org/wiki/Category:Second-hand_bookshops"


def test_seed_requests_parse_each_category_page(tmp_path: Path) -> None:
    seed_file = tmp_path / "commons_categories.toml"
    seed_file.write_text(
        '[[categories]]\nname = "Bookshelves"\nexpected_content = "spine"\n\n'
        '[[categories]]\nname = "ISBN"\nexpected_content = "isbn"\n'
    )

    seed_requests = COMMONS_CATEGORIES_SOURCE.build_seed_requests(seed_file)

    assert summarize(seed_requests) == [
        (CATEGORY_URL, RequestPurpose.PARSE, 0, CATEGORY_LABELS),
        ("https://commons.wikimedia.org/wiki/Category:ISBN", RequestPurpose.PARSE, 0, {"expected_content": "isbn", "category": "ISBN"}),
    ]


def test_category_page_queues_each_photo_file_page_once() -> None:
    html = create_category_page_html("/wiki/File:Shelf.jpg", "/wiki/File:Library.JPG")

    assert summarize(extract_from_page(CATEGORY_URL, html, depth=0)) == [
        ("https://commons.wikimedia.org/wiki/File:Shelf.jpg", RequestPurpose.PARSE, 1, CATEGORY_LABELS),
        ("https://commons.wikimedia.org/wiki/File:Library.JPG", RequestPurpose.PARSE, 1, CATEGORY_LABELS),
    ]


def test_category_page_skips_files_that_are_not_photos() -> None:
    html = create_category_page_html(
        "/wiki/File:Diagram.svg", "/wiki/File:Talk.ogg", "/wiki/File:Scan.pdf", "/wiki/File:ISBN_Details-ar.png"
    )

    assert extract_from_page(CATEGORY_URL, html, depth=0) == []


def test_category_page_without_media_section_queues_nothing() -> None:
    assert extract_from_page(CATEGORY_URL, '<div id="mw-subcategories"></div>', depth=0) == []


def test_file_page_downloads_the_largest_thumbnail_with_its_license() -> None:
    thumbnail_links = [
        ("330 × 248 pixels", f"{THUMBNAIL_BASE_URL}/330px-Shelf.jpg{TRACKING_QUERY}"),
        ("1,280 × 960 pixels", f"{THUMBNAIL_BASE_URL}/1280px-Shelf.jpg{TRACKING_QUERY}"),
        ("3,840 × 2,880 pixels", f"{THUMBNAIL_BASE_URL}/3840px-Shelf.jpg{TRACKING_QUERY}"),
    ]
    html = create_file_page_html(thumbnail_links, '<span class="licensetpl_short">CC BY-SA 4.0 </span>')

    assert summarize(extract_from_page(FILE_PAGE_URL, html, depth=1)) == [
        (
            f"{THUMBNAIL_BASE_URL}/3840px-Shelf.jpg",
            RequestPurpose.DOWNLOAD,
            2,
            {**CATEGORY_LABELS, "file_page_url": FILE_PAGE_URL, "license": "CC BY-SA 4.0"},
        )
    ]


def test_file_page_downloads_the_original_when_thumbnails_are_too_small() -> None:
    html = create_file_page_html([("330 × 227 pixels", f"{THUMBNAIL_BASE_URL}/330px-Shelf.jpg")], "")

    [download_request] = extract_from_page(FILE_PAGE_URL, html, depth=1)

    assert download_request.url == ORIGINAL_URL


def test_file_page_without_license_keeps_an_empty_license() -> None:
    html = create_file_page_html([], "")

    [download_request] = extract_from_page(FILE_PAGE_URL, html, depth=1)

    assert download_request.labels["license"] == ""


def test_file_page_without_original_link_raises_extraction_error() -> None:
    with pytest.raises(ExtractionError):
        extract_from_page(FILE_PAGE_URL, "<html><body>deleted file</body></html>", depth=1)


def test_page_that_is_neither_category_nor_file_raises_extraction_error() -> None:
    with pytest.raises(ExtractionError):
        extract_from_page("https://commons.wikimedia.org/wiki/Main_Page", "<html></html>", depth=0)
