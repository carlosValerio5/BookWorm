import json
import logging
from pathlib import Path

import pytest
import structlog

from bookworm.logging_setup import configure_logging, log_call

TEST_SERVICE_NAME = "bookworm.test_service"


def read_log_events(log_file_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_file_path.read_text().splitlines()]


def test_log_call_writes_started_and_finished_events(tmp_path: Path) -> None:
    log_file_path = tmp_path / "bookworm.jsonl"
    configure_logging(log_file_path)
    logger = structlog.stdlib.get_logger(TEST_SERVICE_NAME)

    with log_call(logger, "do_work"):
        pass

    assert [event["event"] for event in read_log_events(log_file_path)] == ["call_started", "call_finished"]


def test_finished_event_carries_trace_fields(tmp_path: Path) -> None:
    log_file_path = tmp_path / "bookworm.jsonl"
    configure_logging(log_file_path)
    logger = structlog.stdlib.get_logger(TEST_SERVICE_NAME)

    with log_call(logger, "do_work", image_path="cover.jpg"):
        pass

    finished_event = read_log_events(log_file_path)[-1]
    assert finished_event["call"] == "do_work"
    assert finished_event["service"] == TEST_SERVICE_NAME
    assert finished_event["image_path"] == "cover.jpg"
    assert finished_event["level"] == "info"
    assert finished_event["duration_ms"] >= 0
    assert "timestamp" in finished_event


def test_log_call_logs_failure_with_traceback_and_reraises(tmp_path: Path) -> None:
    log_file_path = tmp_path / "bookworm.jsonl"
    configure_logging(log_file_path)
    logger = structlog.stdlib.get_logger(TEST_SERVICE_NAME)

    with pytest.raises(ValueError), log_call(logger, "do_work"):
        raise ValueError("bad cover")

    failed_event = read_log_events(log_file_path)[-1]
    assert failed_event["event"] == "call_failed"
    assert failed_event["level"] == "error"
    assert "ValueError: bad cover" in failed_event["exception"]


def test_bound_scan_id_is_added_to_every_event(tmp_path: Path) -> None:
    log_file_path = tmp_path / "bookworm.jsonl"
    configure_logging(log_file_path)
    logger = structlog.stdlib.get_logger(TEST_SERVICE_NAME)

    with structlog.contextvars.bound_contextvars(scan_id="scan-123"):
        logger.info("something_happened")

    assert read_log_events(log_file_path)[0]["scan_id"] == "scan-123"


def test_third_party_stdlib_logs_are_written_as_json(tmp_path: Path) -> None:
    log_file_path = tmp_path / "bookworm.jsonl"
    configure_logging(log_file_path)

    logging.getLogger("some_library").warning("weights downloaded")

    third_party_event = read_log_events(log_file_path)[0]
    assert third_party_event["service"] == "some_library"
    assert third_party_event["event"] == "weights downloaded"
