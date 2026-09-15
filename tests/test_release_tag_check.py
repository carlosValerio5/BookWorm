from pathlib import Path

import pytest
from check_release_tag import (
    CHANGELOG_PATH,
    PYPROJECT_PATH,
    ReleaseTagError,
    changelog_has_release,
    check_release_tag,
    find_release_tag_problems,
    is_strict_version_tag,
    read_project_version,
)

CHANGELOG_WITH_RELEASE = """# Changelog

## [Unreleased]

## [0.2.0] - 2026-10-01

### Added
- Something.
"""


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("v0.1.0", True),
        ("v1.12.3", True),
        ("v10.0.0", True),
        ("0.1.0", False),
        ("V0.1.0", False),
        ("v0.1", False),
        ("v0.1.0.0", False),
        ("v01.1.0", False),
        ("v0.01.0", False),
        ("v0.1.0-rc.1", False),
        ("v0.1.0a1", False),
        ("v0.1.0+build", False),
        ("release-0.1.0", False),
        ("", False),
    ],
)
def test_is_strict_version_tag(tag: str, expected: bool) -> None:
    assert is_strict_version_tag(tag) is expected


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.2.0", True),
        ("0.1.0", False),
        ("0.2", False),
        ("Unreleased", False),
    ],
)
def test_changelog_has_release_needs_dated_version_heading(version: str, expected: bool) -> None:
    assert changelog_has_release(CHANGELOG_WITH_RELEASE, version) is expected


def test_changelog_has_release_rejects_heading_without_date() -> None:
    assert changelog_has_release("## [0.2.0]\n", "0.2.0") is False


def test_read_project_version(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[project]\nname = "bookworm"\nversion = "0.2.0"\n', encoding="utf-8")

    assert read_project_version(pyproject_path) == "0.2.0"


def test_find_release_tag_problems_is_empty_for_matching_release() -> None:
    assert find_release_tag_problems("v0.2.0", "0.2.0", CHANGELOG_WITH_RELEASE) == []


def test_find_release_tag_problems_reports_tag_that_does_not_match_version() -> None:
    problems = find_release_tag_problems("v0.3.0", "0.2.0", CHANGELOG_WITH_RELEASE)

    assert problems == ["tag 'v0.3.0' does not match pyproject version '0.2.0'"]


def test_find_release_tag_problems_reports_every_problem_at_once() -> None:
    problems = find_release_tag_problems("0.3", "0.3.0", CHANGELOG_WITH_RELEASE)

    assert problems == [
        "tag '0.3' is not vMAJOR.MINOR.PATCH",
        "tag '0.3' does not match pyproject version '0.3.0'",
        "CHANGELOG.md has no '## [0.3.0] - YYYY-MM-DD' section",
    ]


def test_repository_changelog_has_section_for_project_version() -> None:
    project_version = read_project_version(PYPROJECT_PATH)

    assert changelog_has_release(CHANGELOG_PATH.read_text(encoding="utf-8"), project_version)


def test_check_release_tag_passes_for_current_project_version() -> None:
    check_release_tag(f"v{read_project_version(PYPROJECT_PATH)}")


def test_check_release_tag_raises_for_tag_that_does_not_match() -> None:
    with pytest.raises(ReleaseTagError, match="does not match pyproject version"):
        check_release_tag("v999.0.0")
