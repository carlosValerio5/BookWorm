import re
from urllib.parse import urldefrag, urljoin, urlsplit

from selectolax.parser import HTMLParser, Node

WEB_URL_SCHEMES = frozenset({"http", "https"})
WIDTH_DESCRIPTOR = re.compile(r"^(\d+)w$")


def extract_image_urls(page_url: str, html: str) -> list[str]:
    image_sources = [select_best_image_source(node) for node in HTMLParser(html).css("img")]
    return keep_unique_web_urls([urljoin(page_url, source) for source in image_sources if source])


def extract_link_urls(page_url: str, html: str) -> list[str]:
    hrefs = [node.attributes.get("href") or "" for node in HTMLParser(html).css("a")]
    return keep_unique_web_urls([urldefrag(urljoin(page_url, href)).url for href in hrefs if href])


def select_best_image_source(image_node: Node) -> str:
    attributes = image_node.attributes
    return (
        attributes.get("data-orig-file")
        or select_widest_srcset_candidate(attributes.get("srcset") or "")
        or attributes.get("src")
        or ""
    )


def select_widest_srcset_candidate(srcset: str) -> str:
    candidates = [parse_srcset_candidate(candidate) for candidate in srcset.split(",") if candidate.strip()]
    widest_url, _ = max(candidates, key=lambda candidate: candidate[1], default=("", 0))
    return widest_url


def parse_srcset_candidate(candidate: str) -> tuple[str, int]:
    url, _, descriptor = candidate.strip().partition(" ")
    width_match = WIDTH_DESCRIPTOR.match(descriptor.strip())
    return url, int(width_match.group(1)) if width_match else 0


def keep_unique_web_urls(candidate_urls: list[str]) -> list[str]:
    web_urls = [url for url in candidate_urls if urlsplit(url).scheme in WEB_URL_SCHEMES]
    return list(dict.fromkeys(web_urls))
