from pathlib import Path

from crawler_factories import create_crawl_request, create_fetched_response

from bookworm.crawler.crawl_types import CrawlRequest, RequestPurpose
from bookworm.crawler.sources.blog_pages import BLOG_PAGES_SOURCE

SEED_URL = "https://blog.example/category/book-hauls/"
PAGE_LABELS = {
    "expected_content": "cover",
    "seed_url": SEED_URL,
    "follow_link_pattern": r"/\d{4}/\d{2}/\d{2}/[^/]*haul",
}


def extract_from_page(html: str) -> list[CrawlRequest]:
    request = create_crawl_request(url=SEED_URL, source_name=BLOG_PAGES_SOURCE.name, labels=PAGE_LABELS)
    return BLOG_PAGES_SOURCE.extract_requests(create_fetched_response(request, html.encode()))


def test_seed_requests_parse_each_page_with_its_labels(tmp_path: Path) -> None:
    seed_file = tmp_path / "blog_pages.toml"
    seed_file.write_text(
        r"""
[[pages]]
url = "https://blog.example/category/book-hauls/"
expected_content = "cover"
follow_link_pattern = '/\d{4}/\d{2}/\d{2}/[^/]*haul'
"""
    )

    seed_requests = BLOG_PAGES_SOURCE.build_seed_requests(seed_file)

    assert [(request.url, request.purpose, request.depth, request.labels) for request in seed_requests] == [
        (SEED_URL, RequestPurpose.PARSE, 0, PAGE_LABELS)
    ]


def test_extract_downloads_page_images_with_page_labels() -> None:
    [download_request] = extract_from_page('<img src="https://i0.wp.com/blog.example/haul.jpg">')

    assert (download_request.url, download_request.purpose, download_request.depth, download_request.labels) == (
        "https://i0.wp.com/blog.example/haul.jpg",
        RequestPurpose.DOWNLOAD,
        1,
        {**PAGE_LABELS, "page_url": SEED_URL},
    )


def test_extract_drops_images_from_blocked_hosts() -> None:
    html = (
        '<img src="https://pixel.wp.com/g.gif">'
        '<img src="https://secure.gravatar.com/avatar/1">'
        '<img src="https://scontent-lax3-1.cdninstagram.com/photo.jpg">'
    )

    assert extract_from_page(html) == []


def test_extract_follows_same_host_links_matching_the_pattern() -> None:
    html = (
        '<a href="/2021/06/25/half-price-books-flagship-a-book-haul/">haul</a>'
        '<a href="/2019/05/09/the-witch-of-blackbird-pond-a-review/">review</a>'
    )

    [link_request] = extract_from_page(html)

    assert (link_request.url, link_request.purpose, link_request.depth, link_request.labels) == (
        "https://blog.example/2021/06/25/half-price-books-flagship-a-book-haul/",
        RequestPurpose.PARSE,
        1,
        PAGE_LABELS,
    )


def test_extract_ignores_matching_links_on_other_hosts() -> None:
    assert extract_from_page('<a href="https://other.example/2021/06/25/book-haul/">haul</a>') == []
