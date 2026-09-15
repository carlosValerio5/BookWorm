from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from image_factories import create_blank_image, write_heic_image, write_image

from bookworm.annotator.web_app import create_annotator_app

PNG_PHOTO_PATH = "cover/blank.png"
HEIC_PHOTO_PATH = "iphone.heic"
VALID_BOX_JSON = {"x_min": 10, "y_min": 20, "x_max": 200, "y_max": 80}


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
        {"photo_path": PNG_PHOTO_PATH, "annotated": False},
        {"photo_path": HEIC_PHOTO_PATH, "annotated": False},
    ]
    assert after_saving == [
        {"photo_path": PNG_PHOTO_PATH, "annotated": True},
        {"photo_path": HEIC_PHOTO_PATH, "annotated": False},
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
    outside_box = {"x_min": 10, "y_min": 20, "x_max": 500, "y_max": 80}

    response = client.put("/api/annotation", json=build_draft_json(box=outside_box))

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
