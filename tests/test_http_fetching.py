import httpx
import pytest
from crawler_factories import TEST_USER_AGENT, build_mock_client, build_timing_out_client, create_crawl_request

from bookworm.crawler.http_fetching import FetchError, build_http_client, fetch_request

PAGE_URL = "https://blog.example/post"


def test_fetch_returns_status_media_type_and_body() -> None:
    client = build_mock_client({PAGE_URL: (200, "text/html; charset=UTF-8", b"<html></html>")}, [])
    request = create_crawl_request(url=PAGE_URL)

    response = fetch_request(client, request)

    assert (response.request, response.status_code, response.media_type, response.body) == (
        request,
        200,
        "text/html",
        b"<html></html>",
    )


def test_fetch_returns_error_status_without_raising() -> None:
    client = build_mock_client({}, [])

    assert fetch_request(client, create_crawl_request(url=PAGE_URL)).status_code == 404


def test_fetch_keeps_redirects_unfollowed_with_their_absolute_location() -> None:
    client = build_mock_client({}, [], redirect_locations_by_url={PAGE_URL: "/moved"})

    response = fetch_request(client, create_crawl_request(url=PAGE_URL))

    assert (response.status_code, response.redirect_url) == (302, "https://blog.example/moved")


def test_fetch_raises_fetch_error_when_the_body_is_larger_than_the_limit() -> None:
    client = build_mock_client({PAGE_URL: (200, "image/jpeg", b"x" * 2048)}, [])

    with pytest.raises(FetchError):
        fetch_request(client, create_crawl_request(url=PAGE_URL), max_response_bytes=1024)


def test_fetch_raises_fetch_error_on_timeout() -> None:
    with pytest.raises(FetchError):
        fetch_request(build_timing_out_client(), create_crawl_request(url=PAGE_URL))


def test_client_sends_identifying_user_agent() -> None:
    sent_user_agents: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        sent_user_agents.append(request.headers["user-agent"])
        return httpx.Response(200)

    client = build_http_client(TEST_USER_AGENT, transport=httpx.MockTransport(respond))
    fetch_request(client, create_crawl_request(url=PAGE_URL))

    assert sent_user_agents == [TEST_USER_AGENT]
