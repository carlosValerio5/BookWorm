from urllib.parse import urljoin

import httpx
import structlog

from bookworm.crawler.crawl_types import CrawlRequest, FetchedResponse
from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

HTTP_TIMEOUT_SECONDS = 90.0
MAX_RESPONSE_BYTES = 30 * 1024 * 1024


class FetchError(Exception):
    pass


def build_http_client(user_agent: str, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": user_agent},
        timeout=HTTP_TIMEOUT_SECONDS,
        follow_redirects=False,
        transport=transport,
    )


def fetch_request(
    client: httpx.Client, request: CrawlRequest, max_response_bytes: int = MAX_RESPONSE_BYTES
) -> FetchedResponse:
    with log_call(logger, "fetch_request", url=request.url, purpose=str(request.purpose)):
        try:
            with client.stream("GET", request.url) as response:
                body = read_limited_body(response, max_response_bytes)
        except httpx.TransportError as error:
            raise FetchError(f"Could not fetch {request.url}: {error!r}") from error
        fetched_response = FetchedResponse(
            request=request,
            status_code=response.status_code,
            media_type=read_media_type(response),
            body=body,
            redirect_url=read_redirect_url(request.url, response),
        )
        logger.info(
            "response_received",
            url=request.url,
            status_code=fetched_response.status_code,
            media_type=fetched_response.media_type,
            body_bytes=len(fetched_response.body),
            redirect_url=fetched_response.redirect_url,
        )
    return fetched_response


def read_limited_body(response: httpx.Response, max_response_bytes: int) -> bytes:
    body = bytearray()
    for chunk in response.iter_bytes():
        body.extend(chunk)
        if len(body) > max_response_bytes:
            raise FetchError(f"Response from {response.url} is larger than {max_response_bytes} bytes")
    return bytes(body)


def read_media_type(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").split(";")[0].strip().lower()


def read_redirect_url(request_url: str, response: httpx.Response) -> str:
    return urljoin(request_url, response.headers["location"]) if response.has_redirect_location else ""
