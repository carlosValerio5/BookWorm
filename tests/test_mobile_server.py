import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from image_factories import create_blank_image, encode_jpeg_bytes

from bookworm.mobile.server import create_mobile_app

BLANK_JPEG_DATA_URL_PREFIX = "data:image/jpeg;base64,"


def build_scan_payload(image_bytes: bytes) -> dict[str, str]:
    return {"image": BLANK_JPEG_DATA_URL_PREFIX + base64.b64encode(image_bytes).decode()}


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_mobile_app(tmp_path / "photos"))


@pytest.mark.slow
@pytest.mark.usefixtures("book_detector", "text_reader")
def test_scan_endpoint_returns_real_pipeline_result_not_a_stub(client: TestClient) -> None:
    payload = build_scan_payload(encode_jpeg_bytes(create_blank_image()))

    response = client.post("/api/scan", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "unknown"
    assert "title" not in body
    assert "author" not in body
    assert "coverImage" not in body


def test_scan_endpoint_rejects_a_malformed_photo(client: TestClient) -> None:
    response = client.post("/api/scan", json={"image": "not-a-data-url"})

    assert response.status_code == 400


@pytest.mark.slow
@pytest.mark.usefixtures("book_detector", "text_reader")
def test_scan_endpoint_saves_the_photo_to_the_photos_dir(tmp_path: Path) -> None:
    photos_dir = tmp_path / "photos"
    client = TestClient(create_mobile_app(photos_dir))
    payload = build_scan_payload(encode_jpeg_bytes(create_blank_image()))

    response = client.post("/api/scan", json=payload)

    assert response.status_code == 200
    assert list(photos_dir.glob("scan_*.jpg"))


def build_frame_payload(frame_bytes: bytes) -> str:
    return base64.b64encode(frame_bytes).decode()


@pytest.mark.slow
@pytest.mark.usefixtures("book_detector")
def test_live_detect_returns_boxes_for_a_single_base64_frame(client: TestClient) -> None:
    frame_bytes = encode_jpeg_bytes(create_blank_image())

    with client.websocket_connect("/api/live-detect") as websocket:
        websocket.send_text(build_frame_payload(frame_bytes))
        response = websocket.receive_json()

    assert response == {"boxes": []}


def test_live_detect_disconnect_ends_the_session_cleanly(client: TestClient) -> None:
    with client.websocket_connect("/api/live-detect"):
        pass


@pytest.mark.slow
@pytest.mark.usefixtures("book_detector")
def test_live_detect_skips_a_malformed_frame_without_hanging(client: TestClient) -> None:
    good_frame = encode_jpeg_bytes(create_blank_image())

    with client.websocket_connect("/api/live-detect") as websocket:
        websocket.send_text("not-valid-base64!!!")
        websocket.send_text(build_frame_payload(good_frame))
        response = websocket.receive_json()

    assert response == {"boxes": []}


@pytest.mark.slow
@pytest.mark.usefixtures("book_detector")
def test_live_detect_skips_a_frame_that_is_not_a_real_image(client: TestClient) -> None:
    good_frame = encode_jpeg_bytes(create_blank_image())

    with client.websocket_connect("/api/live-detect") as websocket:
        websocket.send_text(build_frame_payload(b"not a jpeg"))
        websocket.send_text(build_frame_payload(good_frame))
        response = websocket.receive_json()

    assert response == {"boxes": []}
