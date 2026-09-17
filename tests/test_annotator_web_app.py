import json
from pathlib import Path

import cv2
import easyocr
import numpy as np
import pytest
from fastapi.testclient import TestClient
from image_factories import create_blank_image, write_heic_image, write_image
from ultralytics import YOLO

from bookworm.annotator import web_app
from bookworm.annotator.annotation_types import BoxType, LabeledBox
from bookworm.annotator.web_app import box_type_for_recognized_text, create_annotator_app, labeled_boxes_from_scan
from bookworm.logging_setup import configure_logging
from bookworm.scan_types import BookDetection, BoundingBox, IsbnBarcode, RecognizedText, ScanKind, ScanResult

PNG_PHOTO_PATH = "cover/blank.png"
HEIC_PHOTO_PATH = "iphone.heic"
VALID_BOX_JSON = {"x_min": 10, "y_min": 20, "x_max": 200, "y_max": 80}
OUTSIDE_BOX_JSON = {"x_min": 10, "y_min": 20, "x_max": 500, "y_max": 80}


@pytest.fixture
def photos_dir(tmp_path: Path) -> Path:
    photos_dir = tmp_path / "photos"
    (photos_dir / "cover").mkdir(parents=True)
    write_image(photos_dir / PNG_PHOTO_PATH, create_blank_image(height=300, width=400))
    write_heic_image(photos_dir / HEIC_PHOTO_PATH, create_blank_image(height=200, width=100))
    return photos_dir


@pytest.fixture
def labels_dir(tmp_path: Path) -> Path:
    return tmp_path / "labels"


@pytest.fixture
def client(photos_dir: Path, labels_dir: Path) -> TestClient:
    return TestClient(create_annotator_app(photos_dir, labels_dir))


@pytest.fixture
def log_file_path(tmp_path: Path) -> Path:
    log_file_path = tmp_path / "annotator.jsonl"
    configure_logging(log_file_path)
    return log_file_path


def build_draft_json(
    photo_path: str = PNG_PHOTO_PATH, box_type: str = "title", box: dict[str, int] = VALID_BOX_JSON
) -> dict[str, object]:
    return {
        "photo_path": photo_path,
        "photo_width": 400,
        "photo_height": 300,
        "kind": "cover",
        "labeling_duration_ms": 41250,
        "boxes": [{"box_type": box_type, "box": box, "text": "El Buscón", "confirmed": True}],
    }


def decode_jpeg(jpeg_bytes: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)


def read_log_events(log_file_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_file_path.read_text(encoding="utf-8").splitlines()]


def test_index_page_is_served(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "BookWorm Annotator" in response.text


def test_static_script_is_served(client: TestClient) -> None:
    response = client.get("/static/annotator.js")

    assert response.status_code == 200


def test_lists_photos_with_annotated_flag(client: TestClient) -> None:
    before_saving = client.get("/api/photos").json()
    client.put("/api/annotation", json=build_draft_json())
    after_saving = client.get("/api/photos").json()

    assert before_saving == [
        {"photo_path": PNG_PHOTO_PATH, "annotated": False, "box_count": 0},
        {"photo_path": HEIC_PHOTO_PATH, "annotated": False, "box_count": 0},
    ]
    assert after_saving == [
        {"photo_path": PNG_PHOTO_PATH, "annotated": True, "box_count": 1},
        {"photo_path": HEIC_PHOTO_PATH, "annotated": False, "box_count": 0},
    ]


@pytest.mark.parametrize(("photo_path", "expected_shape"), [(PNG_PHOTO_PATH, (300, 400, 3)), (HEIC_PHOTO_PATH, (200, 100, 3))])
def test_image_is_served_as_full_size_jpeg(
    client: TestClient, photo_path: str, expected_shape: tuple[int, int, int]
) -> None:
    response = client.get("/api/image", params={"photo": photo_path})

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert decode_jpeg(response.content).shape == expected_shape


def test_image_rejects_path_outside_photos_folder(client: TestClient) -> None:
    assert client.get("/api/image", params={"photo": "../secret.png"}).status_code == 400


def test_image_returns_404_for_missing_photo(client: TestClient) -> None:
    assert client.get("/api/image", params={"photo": "missing.png"}).status_code == 404


def test_image_returns_422_for_file_that_is_not_an_image(client: TestClient, photos_dir: Path) -> None:
    (photos_dir / "broken.jpg").write_bytes(b"not an image")

    assert client.get("/api/image", params={"photo": "broken.jpg"}).status_code == 422


ANY_BOX = BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10)


def build_scan_result(
    books: list[BookDetection], barcodes: list[IsbnBarcode], texts: list[RecognizedText]
) -> ScanResult:
    return ScanResult(
        scan_id="any-scan-id",
        image_path="any/image.jpg",
        kind=ScanKind.UNKNOWN,
        isbn=None,
        books=books,
        barcodes=barcodes,
        texts=texts,
    )


def test_box_type_for_recognized_text_detects_isbn() -> None:
    assert box_type_for_recognized_text("ISBN 978-0-306-40615-7") == BoxType.PRINTED_ISBN


def test_box_type_for_recognized_text_defaults_to_other_text() -> None:
    assert box_type_for_recognized_text("El Buscón") == BoxType.OTHER_TEXT


def test_labeled_boxes_from_scan_maps_a_book_with_empty_text() -> None:
    scan_result = build_scan_result(books=[BookDetection(confidence=0.9, box=ANY_BOX)], barcodes=[], texts=[])

    assert labeled_boxes_from_scan(scan_result) == [LabeledBox(box_type=BoxType.BOOK, box=ANY_BOX, text="", confirmed=False)]


def test_labeled_boxes_from_scan_maps_a_barcode_with_empty_text() -> None:
    scan_result = build_scan_result(books=[], barcodes=[IsbnBarcode(isbn="9780306406157", box=ANY_BOX)], texts=[])

    assert labeled_boxes_from_scan(scan_result) == [LabeledBox(box_type=BoxType.BARCODE, box=ANY_BOX, text="", confirmed=False)]


def test_labeled_boxes_from_scan_maps_isbn_bearing_text_to_printed_isbn() -> None:
    isbn_text = "ISBN 978-0-306-40615-7"
    scan_result = build_scan_result(books=[], barcodes=[], texts=[RecognizedText(text=isbn_text, confidence=0.9, box=ANY_BOX)])

    assert labeled_boxes_from_scan(scan_result) == [
        LabeledBox(box_type=BoxType.PRINTED_ISBN, box=ANY_BOX, text=isbn_text, confirmed=False)
    ]


def test_labeled_boxes_from_scan_maps_plain_text_to_other_text() -> None:
    scan_result = build_scan_result(books=[], barcodes=[], texts=[RecognizedText(text="El Buscón", confidence=0.9, box=ANY_BOX)])

    assert labeled_boxes_from_scan(scan_result) == [
        LabeledBox(box_type=BoxType.OTHER_TEXT, box=ANY_BOX, text="El Buscón", confirmed=False)
    ]


def test_labeled_boxes_from_scan_returns_empty_list_for_empty_scan() -> None:
    assert labeled_boxes_from_scan(build_scan_result(books=[], barcodes=[], texts=[])) == []


def test_labeled_boxes_from_scan_orders_books_then_barcodes_then_texts() -> None:
    scan_result = build_scan_result(
        books=[BookDetection(confidence=0.9, box=ANY_BOX)],
        barcodes=[IsbnBarcode(isbn="9780306406157", box=ANY_BOX)],
        texts=[RecognizedText(text="El Buscón", confidence=0.9, box=ANY_BOX)],
    )

    assert [labeled_box.box_type for labeled_box in labeled_boxes_from_scan(scan_result)] == [
        BoxType.BOOK,
        BoxType.BARCODE,
        BoxType.OTHER_TEXT,
    ]


def test_detections_endpoint_merges_boxes_from_every_detector(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_result = build_scan_result(
        books=[BookDetection(confidence=0.87, box=BoundingBox(x_min=1, y_min=2, x_max=3, y_max=4))],
        barcodes=[IsbnBarcode(isbn="9780306406157", box=BoundingBox(x_min=5, y_min=6, x_max=7, y_max=8))],
        texts=[
            RecognizedText(text="ISBN 978-0-306-40615-7", confidence=0.9, box=BoundingBox(x_min=9, y_min=10, x_max=11, y_max=12)),
            RecognizedText(text="El Buscón", confidence=0.9, box=BoundingBox(x_min=13, y_min=14, x_max=15, y_max=16)),
        ],
    )
    monkeypatch.setattr(web_app, "scan_image", lambda _photo_file, _book_detector, _text_reader: scan_result)

    response = client.get("/api/detections", params={"photo": PNG_PHOTO_PATH})

    assert response.status_code == 200
    assert response.json() == [
        {"box_type": "book", "box": {"x_min": 1, "y_min": 2, "x_max": 3, "y_max": 4}, "text": "", "confirmed": False},
        {"box_type": "barcode", "box": {"x_min": 5, "y_min": 6, "x_max": 7, "y_max": 8}, "text": "", "confirmed": False},
        {
            "box_type": "printed_isbn",
            "box": {"x_min": 9, "y_min": 10, "x_max": 11, "y_max": 12},
            "text": "ISBN 978-0-306-40615-7",
            "confirmed": False,
        },
        {
            "box_type": "other_text",
            "box": {"x_min": 13, "y_min": 14, "x_max": 15, "y_max": 16},
            "text": "El Buscón",
            "confirmed": False,
        },
    ]


def test_detections_returns_404_for_missing_photo(client: TestClient) -> None:
    assert client.get("/api/detections", params={"photo": "missing.png"}).status_code == 404


def test_detections_rejects_path_outside_photos_folder(client: TestClient) -> None:
    assert client.get("/api/detections", params={"photo": "../secret.png"}).status_code == 400


def test_detections_call_is_logged(client: TestClient, log_file_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty_scan_result = build_scan_result(books=[], barcodes=[], texts=[])
    monkeypatch.setattr(web_app, "scan_image", lambda _photo_file, _book_detector, _text_reader: empty_scan_result)

    client.get("/api/detections", params={"photo": PNG_PHOTO_PATH})

    finished_calls = [event["call"] for event in read_log_events(log_file_path) if event["event"] == "call_finished"]
    assert "get_photo_detections" in finished_calls


@pytest.mark.slow
def test_detections_endpoint_with_real_detectors_finds_nothing_in_a_blank_photo(
    client: TestClient, book_detector: YOLO, text_reader: easyocr.Reader
) -> None:
    response = client.get("/api/detections", params={"photo": PNG_PHOTO_PATH})

    assert response.status_code == 200
    assert response.json() == []


def test_annotation_is_404_before_saving(client: TestClient) -> None:
    assert client.get("/api/annotation", params={"photo": PNG_PHOTO_PATH}).status_code == 404


def test_saved_annotation_round_trips(client: TestClient, labels_dir: Path) -> None:
    save_response = client.put("/api/annotation", json=build_draft_json())
    load_response = client.get("/api/annotation", params={"photo": PNG_PHOTO_PATH})

    assert save_response.status_code == 200
    assert save_response.json()["schema_version"] == 1
    assert save_response.json()["saved_at"].endswith("Z")
    assert save_response.json()["boxes"] == build_draft_json()["boxes"]
    assert load_response.json() == save_response.json()
    assert (labels_dir / "cover" / "blank.png.json").exists()


def test_invalid_annotation_returns_problems_and_writes_nothing(client: TestClient, labels_dir: Path) -> None:
    response = client.put("/api/annotation", json=build_draft_json(box=OUTSIDE_BOX_JSON))

    assert response.status_code == 422
    assert response.json() == {"problems": ["box 0 (title) is outside the 400x300 photo"]}
    assert not labels_dir.exists()


def test_save_rejects_unknown_box_type(client: TestClient) -> None:
    assert client.put("/api/annotation", json=build_draft_json(box_type="spine")).status_code == 422


def test_save_returns_404_for_missing_photo(client: TestClient) -> None:
    assert client.put("/api/annotation", json=build_draft_json(photo_path="missing.png")).status_code == 404


def test_save_rejects_path_outside_photos_folder(client: TestClient) -> None:
    assert client.put("/api/annotation", json=build_draft_json(photo_path="../secret.png")).status_code == 400


def test_annotation_rejects_path_outside_photos_folder(client: TestClient) -> None:
    assert client.get("/api/annotation", params={"photo": "../secret.png"}).status_code == 400


def test_expected_client_errors_log_one_warning_each_and_no_call_failed(client: TestClient, log_file_path: Path) -> None:
    client.get("/api/annotation", params={"photo": PNG_PHOTO_PATH})
    client.get("/api/image", params={"photo": "missing.png"})
    client.put("/api/annotation", json=build_draft_json(box=OUTSIDE_BOX_JSON))
    client.put("/api/annotation", json=build_draft_json(box_type="spine"))

    events = read_log_events(log_file_path)
    rejected_events = [event for event in events if event["event"] == "request_rejected"]
    assert [event for event in events if event["event"] == "call_failed"] == []
    assert [(event["level"], event["method"], event["path"], event["status_code"], event["error"]) for event in rejected_events] == [
        ("warning", "GET", "/api/annotation", 404, "AnnotationNotFoundError"),
        ("warning", "GET", "/api/image", 404, "PhotoNotFoundError"),
        ("warning", "PUT", "/api/annotation", 422, "AnnotationProblemsError"),
        ("warning", "PUT", "/api/annotation", 422, "RequestValidationError"),
    ]


def test_unreadable_photo_logs_call_failed(client: TestClient, photos_dir: Path, log_file_path: Path) -> None:
    (photos_dir / "broken.jpg").write_bytes(b"not an image")

    client.get("/api/image", params={"photo": "broken.jpg"})

    failed_events = [event for event in read_log_events(log_file_path) if event["event"] == "call_failed"]
    assert [(event["call"], event["level"]) for event in failed_events] == [
        ("load_image", "error"),
        ("get_photo_image", "error"),
    ]


def test_saving_logs_annotation_saved_with_labeling_duration(client: TestClient, log_file_path: Path) -> None:
    client.put("/api/annotation", json=build_draft_json())

    saved_events = [event for event in read_log_events(log_file_path) if event["event"] == "annotation_saved"]
    assert len(saved_events) == 1
    assert saved_events[0]["service"] == "bookworm.annotator.web_app"
    assert saved_events[0]["kind"] == "cover"
    assert saved_events[0]["box_type_counts"] == {"title": 1}
    assert saved_events[0]["labeling_duration_ms"] == 41250
