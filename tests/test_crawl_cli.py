import json
from pathlib import Path

import httpx
import pytest
from crawler_factories import (
    MISSING_ROBOTS_ROUTE,
    MockRoute,
    build_mock_client,
    create_encoded_image,
    create_openverse_page_body,
    create_openverse_result,
)
from typer.testing import CliRunner

from bookworm.crawler import crawl_cli
from bookworm.crawler.sources.openverse_photos import build_openverse_search_url

runner = CliRunner()

IMAGE_URL = "https://live.staticflickr.com/1/thrift_b.jpg"
IMAGE_ROUTE = (200, "image/jpeg", create_encoded_image(width=1024, height=768))


def build_openverse_routes(image_route: MockRoute) -> dict[str, MockRoute]:
    search_page_body = create_openverse_page_body([create_openverse_result(IMAGE_URL)], page=1, page_count=1)
    return {
        "https://api.openverse.org/robots.txt": MISSING_ROBOTS_ROUTE,
        "https://live.staticflickr.com/robots.txt": MISSING_ROBOTS_ROUTE,
        build_openverse_search_url("thrift books", 1): (200, "application/json", search_page_body),
        IMAGE_URL: image_route,
    }


def use_mock_http(monkeypatch: pytest.MonkeyPatch, routes_by_url: dict[str, MockRoute]) -> None:
    def build_mock_http_client(user_agent: str) -> httpx.Client:
        return build_mock_client(routes_by_url, [])

    monkeypatch.setattr(crawl_cli, "build_http_client", build_mock_http_client)
    monkeypatch.setattr(crawl_cli, "resolve_host_addresses", lambda host: ["93.184.216.34"])


def build_run_arguments(tmp_path: Path, source_name: str = "openverse_photos") -> list[str]:
    seed_file = tmp_path / "queries.toml"
    seed_file.write_text('[[queries]]\ntext = "thrift books"\nexpected_content = "cover"\n')
    return [
        "run",
        source_name,
        "--seed-file",
        str(seed_file),
        "--max-requests",
        "10",
        "--state-db",
        str(tmp_path / "crawl_state.sqlite3"),
        "--dataset-dir",
        str(tmp_path / "crawled"),
    ]


def test_run_rejects_an_unknown_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKWORM_CRAWLER_CONTACT", "tester@example.com")

    result = runner.invoke(crawl_cli.app, build_run_arguments(tmp_path, source_name="ebay"))

    assert result.exit_code == 2


def test_run_requires_a_contact_for_the_user_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOOKWORM_CRAWLER_CONTACT", raising=False)

    result = runner.invoke(crawl_cli.app, build_run_arguments(tmp_path))

    assert result.exit_code == 2


def test_run_collects_openverse_photos_and_prints_the_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKWORM_CRAWLER_CONTACT", "tester@example.com")
    use_mock_http(monkeypatch, build_openverse_routes(IMAGE_ROUTE))

    result = runner.invoke(crawl_cli.app, build_run_arguments(tmp_path))

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"requests_handled": 2, "files_saved": 1, "stop_reason": "queue_empty"}


def test_retry_failed_downloads_what_failed_before(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKWORM_CRAWLER_CONTACT", "tester@example.com")
    use_mock_http(monkeypatch, build_openverse_routes((500, "text/plain", b"oops")))
    runner.invoke(crawl_cli.app, build_run_arguments(tmp_path))
    use_mock_http(monkeypatch, build_openverse_routes(IMAGE_ROUTE))

    result = runner.invoke(crawl_cli.app, [*build_run_arguments(tmp_path), "--retry-failed"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["files_saved"] == 1


def test_status_prints_request_and_saved_file_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOKWORM_CRAWLER_CONTACT", "tester@example.com")
    use_mock_http(monkeypatch, build_openverse_routes(IMAGE_ROUTE))
    runner.invoke(crawl_cli.app, build_run_arguments(tmp_path))

    result = runner.invoke(crawl_cli.app, ["status", "--state-db", str(tmp_path / "crawl_state.sqlite3")])

    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {
        "requests": {"openverse_photos": {"done": 2}},
        "saved_files": [{"source_name": "openverse_photos", "expected_content": "cover", "count": 1}],
    }
