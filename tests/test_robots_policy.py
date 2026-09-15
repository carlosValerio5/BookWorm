from crawler_factories import build_mock_client, build_timing_out_client

from bookworm.crawler.robots_policy import RobotsPolicy

ROBOTS_URL = "https://blog.example/robots.txt"
ROBOTS_BODY = b"User-agent: *\nDisallow: /private/\n"


def test_disallowed_path_is_not_allowed() -> None:
    client = build_mock_client({ROBOTS_URL: (200, "text/plain", ROBOTS_BODY)}, [])

    assert RobotsPolicy(client).is_url_allowed("https://blog.example/private/photo.jpg") is False


def test_other_path_is_allowed() -> None:
    client = build_mock_client({ROBOTS_URL: (200, "text/plain", ROBOTS_BODY)}, [])

    assert RobotsPolicy(client).is_url_allowed("https://blog.example/2026/07/haul/") is True


def test_missing_robots_file_allows_everything() -> None:
    client = build_mock_client({ROBOTS_URL: (404, "text/html", b"not found")}, [])

    assert RobotsPolicy(client).is_url_allowed("https://blog.example/private/photo.jpg") is True


def test_robots_server_error_disallows_everything() -> None:
    client = build_mock_client({ROBOTS_URL: (503, "text/html", b"unavailable")}, [])

    assert RobotsPolicy(client).is_url_allowed("https://blog.example/2026/07/haul/") is False


def test_unreachable_robots_file_disallows_everything() -> None:
    assert RobotsPolicy(build_timing_out_client()).is_url_allowed("https://blog.example/2026/07/haul/") is False


def test_robots_file_is_fetched_once_per_host() -> None:
    requested_urls: list[str] = []
    policy = RobotsPolicy(build_mock_client({ROBOTS_URL: (200, "text/plain", ROBOTS_BODY)}, requested_urls))

    policy.is_url_allowed("https://blog.example/1")
    policy.is_url_allowed("https://blog.example/2")

    assert requested_urls == [ROBOTS_URL]
