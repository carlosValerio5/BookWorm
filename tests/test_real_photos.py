from pathlib import Path

import easyocr
import pytest
from ultralytics import YOLO

from bookworm.scan_classification import scan_image
from bookworm.scan_types import ScanKind

DATASET_DIRECTORY = Path(__file__).resolve().parents[1] / "dataset"


def list_real_photos(kind_folder_pattern: str) -> list[Path]:
    return sorted(
        photo_path
        for photo_path in DATASET_DIRECTORY.glob(f"{kind_folder_pattern}/*")
        if photo_path.is_file() and not photo_path.name.startswith(".")
    )


def describe_photo(photo_path: Path) -> str:
    return f"{photo_path.parent.name}/{photo_path.name}"


@pytest.mark.slow
@pytest.mark.parametrize("photo_path", list_real_photos("*"), ids=describe_photo)
def test_real_photo_kind_matches_its_folder(
    photo_path: Path, book_detector: YOLO, text_reader: easyocr.Reader
) -> None:
    result = scan_image(photo_path, book_detector, text_reader)

    assert result.kind == ScanKind(photo_path.parent.name)


@pytest.mark.slow
@pytest.mark.parametrize("photo_path", list_real_photos("isbn"), ids=describe_photo)
def test_real_isbn_photo_reads_isbn_from_file_name(
    photo_path: Path, book_detector: YOLO, text_reader: easyocr.Reader
) -> None:
    result = scan_image(photo_path, book_detector, text_reader)

    assert result.isbn == photo_path.stem
