import json
import struct

import cv2
import httpx
import numpy as np

from bookworm.crawler.crawl_types import CrawlRequest, FetchedResponse, RequestPurpose, SavedFile
from bookworm.crawler.http_fetching import build_http_client

TEST_SOURCE_NAME = "test_source"
TEST_USER_AGENT = "bookworm-crawler/test (+tester@example.com)"
MISSING_ROBOTS_ROUTE = (404, "text/plain", b"")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

MockRoute = tuple[int, str, bytes]


def create_encoded_image(width: int, height: int, extension: str = ".jpg") -> bytes:
    pixels = np.full((height, width, 3), 200, dtype=np.uint8)
    _, encoded_image = cv2.imencode(extension, pixels)
    return encoded_image.tobytes()


def create_png_header(width: int, height: int) -> bytes:
    image_header_fields = struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00"
    return PNG_SIGNATURE + struct.pack(">I", 13) + b"IHDR" + image_header_fields + b"\x00\x00\x00\x00"


def create_crawl_request(
    url: str = "https://blog.example/post",
    purpose: RequestPurpose = RequestPurpose.PARSE,
    depth: int = 0,
    labels: dict[str, str] | None = None,
    source_name: str = TEST_SOURCE_NAME,
) -> CrawlRequest:
    return CrawlRequest(url=url, source_name=source_name, purpose=purpose, depth=depth, labels=labels or {})


def create_fetched_response(
    request: CrawlRequest, body: bytes, media_type: str = "text/html", status_code: int = 200
) -> FetchedResponse:
    return FetchedResponse(request=request, status_code=status_code, media_type=media_type, body=body)


def create_saved_file(content_sha256: str = "a" * 64, expected_content: str = "cover") -> SavedFile:
    return SavedFile(
        content_sha256=content_sha256,
        file_path=f"dataset/crawled/{TEST_SOURCE_NAME}/{content_sha256}.jpg",
        source_name=TEST_SOURCE_NAME,
        source_url=f"https://img.example/{content_sha256}.jpg",
        labels={"expected_content": expected_content},
    )


def create_openverse_result(
    image_url: str, width: int | None = 1024, height: int | None = 768, mature: bool = False
) -> dict:
    return {
        "id": "result-" + image_url.rsplit("/", 1)[-1],
        "title": "Thrift Books",
        "url": image_url,
        "foreign_landing_url": "https://www.flickr.com/photos/someone/1",
        "creator": "someone",
        "license": "by",
        "license_version": "2.0",
        "provider": "flickr",
        "source": "flickr",
        "mature": mature,
        "width": width,
        "height": height,
    }


def create_openverse_page_body(results: list[dict], page: int, page_count: int) -> bytes:
    body = {"result_count": page_count * 20, "page_count": page_count, "page_size": 20, "page": page, "results": results}
    return json.dumps(body).encode()


def build_mock_client(
    routes_by_url: dict[str, MockRoute],
    requested_urls: list[str],
    timing_out_urls: frozenset[str] = frozenset(),
    redirect_locations_by_url: dict[str, str] | None = None,
) -> httpx.Client:
    redirect_locations = redirect_locations_by_url or {}

    def respond(request: httpx.Request) -> httpx.Response:
        requested_url = str(request.url)
        requested_urls.append(requested_url)
        if requested_url in timing_out_urls:
            raise httpx.ReadTimeout("read timed out", request=request)
        if requested_url in redirect_locations:
            return httpx.Response(302, headers={"location": redirect_locations[requested_url]})
        status_code, media_type, body = routes_by_url.get(requested_url, (404, "text/plain", b""))
        return httpx.Response(status_code, headers={"content-type": media_type}, content=body)

    return build_http_client(TEST_USER_AGENT, transport=httpx.MockTransport(respond))


def build_timing_out_client() -> httpx.Client:
    def time_out(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=request)

    return build_http_client(TEST_USER_AGENT, transport=httpx.MockTransport(time_out))
