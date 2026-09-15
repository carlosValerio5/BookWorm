import httpx
import structlog

from bookworm.crawler.crawl_types import CrawlRequest, FetchedResponse
from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

HTTP_TIMEOUT_SECONDS = 90.0


class FetchError(Exception):
    pass


def build_http_client(user_agent: str, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": user_agent},
        timeout=HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
        transport=transport,
    )


def fetch_request(client: httpx.Client, request: CrawlRequest) -> FetchedResponse:
    with log_call(logger, "fetch_request", url=request.url, purpose=str(request.purpose)):
        try:
            response = client.get(request.url)
        except httpx.TransportError as error:
            raise FetchError(f"Could not fetch {request.url}: {error!r}") from error
        fetched_response = FetchedResponse(
            request=request,
            status_code=response.status_code,
            media_type=read_media_type(response),
            body=response.content,
        )
        logger.info(
            "response_received",
            url=request.url,
            status_code=fetched_response.status_code,
            media_type=fetched_response.media_type,
            body_bytes=len(fetched_response.body),
        )
    return fetched_response


def read_media_type(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").split(";")[0].strip().lower()
