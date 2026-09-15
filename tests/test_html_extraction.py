from bookworm.crawler.html_extraction import extract_image_urls, extract_link_urls

PAGE_URL = "https://blog.example/2026/07/haul/"


def test_image_urls_are_made_absolute() -> None:
    html = '<img src="/uploads/haul.jpg">'

    assert extract_image_urls(PAGE_URL, html) == ["https://blog.example/uploads/haul.jpg"]


def test_image_url_prefers_the_widest_srcset_candidate() -> None:
    html = '<img src="/haul-300.jpg" srcset="/haul-300.jpg 300w, /haul-1024.jpg 1024w, /haul-768.jpg 768w">'

    assert extract_image_urls(PAGE_URL, html) == ["https://blog.example/haul-1024.jpg"]


def test_image_url_prefers_the_wordpress_original_file() -> None:
    html = (
        '<img src="/haul.jpg?w=630" srcset="/haul.jpg?w=630 630w, /haul.jpg?w=1260 1260w"'
        ' data-orig-file="https://blog.example/uploads/haul.jpg">'
    )

    assert extract_image_urls(PAGE_URL, html) == ["https://blog.example/uploads/haul.jpg"]


def test_image_urls_skip_data_uris() -> None:
    html = '<img src="data:image/gif;base64,R0lGOD"><img src="/haul.jpg">'

    assert extract_image_urls(PAGE_URL, html) == ["https://blog.example/haul.jpg"]


def test_image_urls_are_deduplicated_in_page_order() -> None:
    html = '<img src="/b.jpg"><img src="/a.jpg"><img src="/b.jpg">'

    assert extract_image_urls(PAGE_URL, html) == ["https://blog.example/b.jpg", "https://blog.example/a.jpg"]


def test_link_urls_drop_fragments_and_non_web_links() -> None:
    html = (
        '<a href="/2026/08/haul/#comments">x</a>'
        '<a href="mailto:me@example.com">x</a>'
        '<a href="javascript:void(0)">x</a>'
    )

    assert extract_link_urls(PAGE_URL, html) == ["https://blog.example/2026/08/haul/"]
