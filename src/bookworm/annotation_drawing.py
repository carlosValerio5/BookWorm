import cv2
import numpy as np
import structlog

from bookworm.logging_setup import log_call
from bookworm.scan_types import BoundingBox, ScanKind, ScanResult

logger = structlog.stdlib.get_logger(__name__)

BOOK_COLOR = (0, 200, 0)
BARCODE_COLOR = (0, 0, 255)
TEXT_COLOR = (255, 128, 0)
BANNER_COLOR = (0, 0, 0)
BOX_THICKNESS = 2
LABEL_FONT = cv2.FONT_HERSHEY_SIMPLEX
LABEL_FONT_SCALE = 0.5
LABEL_OFFSET_ABOVE_BOX = 6
LABEL_MINIMUM_BASELINE = 12
BANNER_FONT_SCALE = 0.8
BANNER_ORIGIN = (10, 30)


def draw_scan_result(image: np.ndarray, scan_result: ScanResult) -> np.ndarray:
    with log_call(logger, "draw_scan_result", scan_id=scan_result.scan_id):
        annotated_image = image.copy()
        for book in scan_result.books:
            draw_labeled_box(annotated_image, book.box, f"book {book.confidence:.2f}", BOOK_COLOR)
        for barcode in scan_result.barcodes:
            draw_labeled_box(annotated_image, barcode.box, f"ISBN {barcode.isbn}", BARCODE_COLOR)
        for text in scan_result.texts:
            draw_labeled_box(annotated_image, text.box, text.text, TEXT_COLOR)
        draw_scan_kind_banner(annotated_image, scan_result.kind)
    return annotated_image


def draw_labeled_box(image: np.ndarray, box: BoundingBox, label: str, color: tuple[int, int, int]) -> None:
    cv2.rectangle(image, (box.x_min, box.y_min), (box.x_max, box.y_max), color, BOX_THICKNESS)
    label_origin = (box.x_min, max(box.y_min - LABEL_OFFSET_ABOVE_BOX, LABEL_MINIMUM_BASELINE))
    cv2.putText(image, label, label_origin, LABEL_FONT, LABEL_FONT_SCALE, color, 1, cv2.LINE_AA)


def draw_scan_kind_banner(image: np.ndarray, kind: ScanKind) -> None:
    cv2.putText(image, f"kind: {kind}", BANNER_ORIGIN, LABEL_FONT, BANNER_FONT_SCALE, BANNER_COLOR, 2, cv2.LINE_AA)
