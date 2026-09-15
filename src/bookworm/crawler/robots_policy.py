from dataclasses import dataclass, field
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import structlog

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

ROBOTS_USER_AGENT_TOKEN = "bookworm-crawler"
DISALLOW_EVERYTHING_RULE_LINES = ["User-agent: *", "Disallow: /"]
ALLOW_EVERYTHING_RULE_LINES: list[str] = []


@dataclass
class RobotsPolicy:
    client: httpx.Client
    rules_by_origin: dict[str, RobotFileParser] = field(default_factory=dict)

    def is_url_allowed(self, url: str) -> bool:
        origin = build_origin(url)
        if origin not in self.rules_by_origin:
            self.rules_by_origin[origin] = fetch_robots_rules(self.client, origin)
        return self.rules_by_origin[origin].can_fetch(ROBOTS_USER_AGENT_TOKEN, url)


def build_origin(url: str) -> str:
    url_parts = urlsplit(url)
    return f"{url_parts.scheme}://{url_parts.netloc}"


def fetch_robots_rules(client: httpx.Client, origin: str) -> RobotFileParser:
    robots_url = f"{origin}/robots.txt"
    with log_call(logger, "fetch_robots_rules", robots_url=robots_url):
        rules = RobotFileParser(robots_url)
        rules.parse(read_robots_rule_lines(client, robots_url))
    return rules


def read_robots_rule_lines(client: httpx.Client, robots_url: str) -> list[str]:
    try:
        response = client.get(robots_url, follow_redirects=True)
    except httpx.TransportError as error:
        logger.warning("robots_unreachable_disallowing_origin", robots_url=robots_url, error=repr(error))
        return DISALLOW_EVERYTHING_RULE_LINES
    logger.info("robots_response_received", robots_url=robots_url, status_code=response.status_code)
    return select_rule_lines_for_status(response)


def select_rule_lines_for_status(response: httpx.Response) -> list[str]:
    rule_lines_by_status_class = {2: response.text.splitlines(), 4: ALLOW_EVERYTHING_RULE_LINES}
    return rule_lines_by_status_class.get(response.status_code // 100, DISALLOW_EVERYTHING_RULE_LINES)
