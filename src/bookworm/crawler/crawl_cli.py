import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from bookworm.crawler.crawl_loop import CrawlContext, run_crawl
from bookworm.crawler.crawl_state import (
    count_requests_by_status,
    count_saved_files_by_expected_content,
    enqueue_requests,
    list_source_names,
    open_crawl_state,
    reset_failed_requests,
)
from bookworm.crawler.http_fetching import build_http_client
from bookworm.crawler.request_pacing import HostPacer
from bookworm.crawler.robots_policy import RobotsPolicy
from bookworm.crawler.sources import SOURCES_BY_NAME
from bookworm.logging_setup import configure_logging

CRAWLER_VERSION = "0.1"
DEFAULT_DATASET_DIR = Path("dataset/crawled")
DEFAULT_STATE_DB = DEFAULT_DATASET_DIR / "crawl_state.sqlite3"

app = typer.Typer(no_args_is_help=True, help="Collect candidate training photos from deterministic sources.")


def validate_source_name(source_name: str) -> str:
    if source_name not in SOURCES_BY_NAME:
        raise typer.BadParameter(f"Unknown source {source_name!r}. Choose one of: {', '.join(sorted(SOURCES_BY_NAME))}")
    return source_name


def build_user_agent(contact: str) -> str:
    return f"bookworm-crawler/{CRAWLER_VERSION} (+{contact})"


@app.command()
def run(
    source_name: Annotated[str, typer.Argument(callback=validate_source_name)],
    seed_file: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    contact: Annotated[
        str, typer.Option(envvar="BOOKWORM_CRAWLER_CONTACT", help="Email or URL in the User-Agent so site owners can reach us.")
    ],
    max_requests: Annotated[int, typer.Option(min=1)] = 50,
    retry_failed: bool = False,
    state_db: Path = DEFAULT_STATE_DB,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
) -> None:
    """Crawl one source until its queue is empty, the request budget is used, or a site rate-limits us."""
    source = SOURCES_BY_NAME[source_name]
    connection = open_crawl_state(state_db)
    enqueue_requests(connection, source.build_seed_requests(seed_file))
    if retry_failed:
        reset_failed_requests(connection, source.name)
    client = build_http_client(build_user_agent(contact))
    context = CrawlContext(
        source=source,
        connection=connection,
        client=client,
        robots_policy=RobotsPolicy(client),
        pacer=HostPacer(min_seconds_between_requests=source.min_seconds_between_requests),
        dataset_dir=dataset_dir,
    )
    typer.echo(json.dumps(asdict(run_crawl(context, max_requests))))


@app.command()
def status(state_db: Path = DEFAULT_STATE_DB) -> None:
    """Print request counts per source and saved file counts per expected content."""
    connection = open_crawl_state(state_db)
    requests_by_source = {
        source_name: count_requests_by_status(connection, source_name) for source_name in list_source_names(connection)
    }
    saved_files = [
        {"source_name": source_name, "expected_content": expected_content, "count": count}
        for (source_name, expected_content), count in count_saved_files_by_expected_content(connection).items()
    ]
    typer.echo(json.dumps({"requests": requests_by_source, "saved_files": saved_files}, indent=2))


def main() -> None:
    configure_logging()
    app()
