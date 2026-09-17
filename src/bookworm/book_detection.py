from functools import cache
from pathlib import Path

import numpy as np
import structlog
from ultralytics import YOLO
from ultralytics.engine.results import Boxes

from bookworm.logging_setup import log_call
from bookworm.scan_types import BookDetection, BoundingBox

logger = structlog.stdlib.get_logger(__name__)

BOOK_DETECTOR_WEIGHTS_PATH = Path("models/book_detector.pt")
COCO_BOOK_CLASS_NAME = "book"
MINIMUM_BOOK_CONFIDENCE = 0.25


@cache
def load_book_detector(weights_path: Path = BOOK_DETECTOR_WEIGHTS_PATH) -> YOLO:
    with log_call(logger, "load_book_detector", weights_path=str(weights_path)):
        weights_path.parent.mkdir(parents=True, exist_ok=True)
        return YOLO(weights_path)


def find_class_id(class_names: dict[int, str], class_name: str) -> int:
    return next(class_id for class_id, name in class_names.items() if name == class_name)


def detect_books(image: np.ndarray, book_detector: YOLO) -> list[BookDetection]:
    with log_call(logger, "detect_books"):
        book_class_id = find_class_id(book_detector.names, COCO_BOOK_CLASS_NAME)
        prediction = book_detector.predict(
            image, classes=[book_class_id], conf=MINIMUM_BOOK_CONFIDENCE, verbose=False
        )[0]
        books = convert_boxes_to_book_detections(prediction.boxes)
        logger.info("books_detected", book_count=len(books), confidences=[book.confidence for book in books])
    return books


def convert_boxes_to_book_detections(boxes: Boxes) -> list[BookDetection]:
    return [
        BookDetection(
            confidence=round(confidence, 4),
            box=BoundingBox.from_points([(x_min, y_min), (x_max, y_max)]),
        )
        for (x_min, y_min, x_max, y_max), confidence in zip(boxes.xyxy.tolist(), boxes.conf.tolist())
    ]
