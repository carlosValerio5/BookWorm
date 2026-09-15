import re
import sys
import tomllib
from pathlib import Path

import structlog

from bookworm.logging_setup import configure_logging, log_call

logger = structlog.stdlib.get_logger("scripts.check_release_tag")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"
STRICT_VERSION_TAG_PATTERN = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


class ReleaseTagError(Exception):
    pass


def is_strict_version_tag(tag: str) -> bool:
    return STRICT_VERSION_TAG_PATTERN.fullmatch(tag) is not None


def read_project_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)["project"]["version"]


def changelog_has_release(changelog_text: str, version: str) -> bool:
    release_heading = re.compile(rf"^## \[{re.escape(version)}\] - [0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$", re.MULTILINE)
    return release_heading.search(changelog_text) is not None


def find_release_tag_problems(tag: str, project_version: str, changelog_text: str) -> list[str]:
    checks = [
        (is_strict_version_tag(tag), f"tag {tag!r} is not vMAJOR.MINOR.PATCH"),
        (tag == f"v{project_version}", f"tag {tag!r} does not match pyproject version {project_version!r}"),
        (
            changelog_has_release(changelog_text, project_version),
            f"CHANGELOG.md has no '## [{project_version}] - YYYY-MM-DD' section",
        ),
    ]
    return [problem for check_passed, problem in checks if not check_passed]


def check_release_tag(tag: str) -> None:
    with log_call(logger, "check_release_tag", tag=tag):
        project_version = read_project_version(PYPROJECT_PATH)
        problems = find_release_tag_problems(tag, project_version, CHANGELOG_PATH.read_text(encoding="utf-8"))
        logger.info("release_tag_checked", tag=tag, project_version=project_version, problems=problems)
        if problems:
            raise ReleaseTagError("; ".join(problems))


def main() -> None:
    configure_logging()
    check_release_tag(sys.argv[1])


if __name__ == "__main__":
    main()
