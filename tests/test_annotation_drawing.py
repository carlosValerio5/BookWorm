from dataclasses import replace

import numpy as np

from bookworm.annotation_drawing import BARCODE_COLOR, BOOK_COLOR, TEXT_COLOR, draw_scan_result
from bookworm.scan_types import BookDetection, BoundingBox, IsbnBarcode, RecognizedText, ScanKind, ScanResult

EMPTY_SCAN_RESULT = ScanResult(
    scan_id="scan-1",
    image_path="photo.png",
    kind=ScanKind.UNKNOWN,
    isbn=None,
    books=[],
    barcodes=[],
    texts=[],
)
DRAWN_BOX = BoundingBox(x_min=50, y_min=60, x_max=150, y_max=160)
LEFT_EDGE_PIXEL = (110, 50)


def test_draw_does_not_modify_original_image(blank_image: np.ndarray) -> None:
    original_image = blank_image.copy()
    result = replace(EMPTY_SCAN_RESULT, books=[BookDetection(confidence=0.9, box=DRAWN_BOX)])

    draw_scan_result(blank_image, result)

    assert np.array_equal(blank_image, original_image)


def test_draws_book_box_in_book_color(blank_image: np.ndarray) -> None:
    result = replace(EMPTY_SCAN_RESULT, books=[BookDetection(confidence=0.9, box=DRAWN_BOX)])

    annotated_image = draw_scan_result(blank_image, result)

    assert tuple(annotated_image[LEFT_EDGE_PIXEL]) == BOOK_COLOR


def test_draws_barcode_box_in_barcode_color(blank_image: np.ndarray) -> None:
    result = replace(EMPTY_SCAN_RESULT, barcodes=[IsbnBarcode(isbn="9780306406157", box=DRAWN_BOX)])

    annotated_image = draw_scan_result(blank_image, result)

    assert tuple(annotated_image[LEFT_EDGE_PIXEL]) == BARCODE_COLOR


def test_draws_text_box_in_text_color(blank_image: np.ndarray) -> None:
    result = replace(EMPTY_SCAN_RESULT, texts=[RecognizedText(text="ISBN", confidence=0.9, box=DRAWN_BOX)])

    annotated_image = draw_scan_result(blank_image, result)

    assert tuple(annotated_image[LEFT_EDGE_PIXEL]) == TEXT_COLOR


def test_draws_scan_kind_banner_even_without_boxes(blank_image: np.ndarray) -> None:
    annotated_image = draw_scan_result(blank_image, EMPTY_SCAN_RESULT)

    assert not np.array_equal(annotated_image, blank_image)
