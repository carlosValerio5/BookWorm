from pathlib import Path

import easyocr
import numpy as np
import pytest
from image_factories import VALID_ISBN13, place_on_white_canvas, write_image
from ultralytics import YOLO

from bookworm.scan_classification import decide_scan_kind, find_isbn, scan_image
from bookworm.scan_types import BookDetection, BoundingBox, IsbnBarcode, RecognizedText, ScanKind

ANY_BOX = BoundingBox(x_min=0, y_min=0, x_max=10, y_max=10)
ANY_BOOK = BookDetection(confidence=0.9, box=ANY_BOX)


def test_find_isbn_prefers_barcode_over_text() -> None:
    barcodes = [IsbnBarcode(isbn=VALID_ISBN13, box=ANY_BOX)]
    texts = [RecognizedText(text="ISBN 978-0-8044-2957-3", confidence=0.9, box=ANY_BOX)]

    assert find_isbn(barcodes, texts) == VALID_ISBN13


def test_find_isbn_reads_isbn_split_across_text_lines() -> None:
    texts = [
        RecognizedText(text="ISBN 978-0-306", confidence=0.9, box=ANY_BOX),
        RecognizedText(text="40615-7", confidence=0.9, box=ANY_BOX),
    ]

    assert find_isbn([], texts) == VALID_ISBN13


def test_find_isbn_returns_none_without_isbn_evidence() -> None:
    texts = [RecognizedText(text="The Great Gatsby", confidence=0.9, box=ANY_BOX)]

    assert find_isbn([], texts) is None


def test_scan_kind_is_isbn_when_isbn_found_even_with_book() -> None:
    assert decide_scan_kind(VALID_ISBN13, [ANY_BOOK]) == ScanKind.ISBN


def test_scan_kind_is_cover_when_book_found_without_isbn() -> None:
    assert decide_scan_kind(None, [ANY_BOOK]) == ScanKind.COVER


def test_scan_kind_is_unknown_without_book_or_isbn() -> None:
    assert decide_scan_kind(None, []) == ScanKind.UNKNOWN


@pytest.mark.slow
def test_scan_image_classifies_barcode_photo_as_isbn(
    tmp_path: Path, isbn_barcode_image: np.ndarray, book_detector: YOLO, text_reader: easyocr.Reader
) -> None:
    image_path = write_image(tmp_path / "barcode.png", place_on_white_canvas(isbn_barcode_image, top=80, left=80))

    result = scan_image(image_path, book_detector, text_reader)

    assert (result.kind, result.isbn) == (ScanKind.ISBN, VALID_ISBN13)


@pytest.mark.slow
def test_scan_image_classifies_blank_photo_as_unknown(
    tmp_path: Path, blank_image: np.ndarray, book_detector: YOLO, text_reader: easyocr.Reader
) -> None:
    image_path = write_image(tmp_path / "blank.png", blank_image)

    result = scan_image(image_path, book_detector, text_reader)

    assert result.kind == ScanKind.UNKNOWN
