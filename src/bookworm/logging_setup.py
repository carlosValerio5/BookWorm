import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import structlog
from structlog.typing import EventDict, WrappedLogger

DEFAULT_LOG_FILE_PATH = Path("logs/bookworm.jsonl")


def rename_logger_to_service(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    event_dict["service"] = event_dict.pop("logger")
    return event_dict


SHARED_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    rename_logger_to_service,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.format_exc_info,
]


def configure_logging(log_file_path: Path = DEFAULT_LOG_FILE_PATH, level: int = logging.INFO) -> None:
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    json_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    handlers = [logging.StreamHandler(sys.stderr), logging.FileHandler(log_file_path, encoding="utf-8")]
    for handler in handlers:
        handler.setFormatter(json_formatter)
    logging.basicConfig(handlers=handlers, level=level, force=True)
    structlog.configure(
        processors=[*SHARED_PROCESSORS, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def calculate_elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)


@contextmanager
def log_call(logger: structlog.stdlib.BoundLogger, call_name: str, **call_fields: object) -> Iterator[None]:
    started_at = time.perf_counter()
    logger.info("call_started", call=call_name, **call_fields)
    try:
        yield
    except Exception:
        logger.exception("call_failed", call=call_name, duration_ms=calculate_elapsed_ms(started_at), **call_fields)
        raise
    logger.info("call_finished", call=call_name, duration_ms=calculate_elapsed_ms(started_at), **call_fields)
