import re
from pathlib import Path

import pytest

from bookworm.crawler.sources import SOURCES_BY_NAME

SEED_DIRECTORY = Path(__file__).parents[1] / "crawler_seeds"
SEED_FILE_BY_SOURCE_NAME = {
    "openverse_photos": SEED_DIRECTORY / "openverse_queries.toml",
    "blog_pages": SEED_DIRECTORY / "blog_pages.toml",
    "commons_categories": SEED_DIRECTORY / "commons_categories.toml",
}
EXPECTED_CONTENT_VALUES = {"cover", "isbn", "spine"}


def test_every_source_has_a_committed_seed_file() -> None:
    assert set(SOURCES_BY_NAME) == set(SEED_FILE_BY_SOURCE_NAME)


@pytest.mark.parametrize("source_name", sorted(SEED_FILE_BY_SOURCE_NAME))
def test_committed_seed_file_builds_labeled_requests(source_name: str) -> None:
    seed_requests = SOURCES_BY_NAME[source_name].build_seed_requests(SEED_FILE_BY_SOURCE_NAME[source_name])

    assert seed_requests
    assert {request.labels["expected_content"] for request in seed_requests} <= EXPECTED_CONTENT_VALUES


def test_committed_blog_link_patterns_compile() -> None:
    seed_requests = SOURCES_BY_NAME["blog_pages"].build_seed_requests(SEED_FILE_BY_SOURCE_NAME["blog_pages"])

    for request in seed_requests:
        re.compile(request.labels["follow_link_pattern"])
