import numpy as np
import pytest
import torch
from ultralytics import YOLO
from ultralytics.engine.results import Boxes

from bookworm.book_detection import convert_boxes_to_book_detections, detect_books, find_class_id
from bookworm.scan_types import BookDetection, BoundingBox

IMAGE_SHAPE = (480, 640)
COCO_BOOK_CLASS_ID = 73.0


def test_converts_yolo_boxes_to_book_detections() -> None:
    boxes = Boxes(torch.tensor([[10.4, 20.6, 110.2, 220.9, 0.91, COCO_BOOK_CLASS_ID]]), orig_shape=IMAGE_SHAPE)

    assert convert_boxes_to_book_detections(boxes) == [
        BookDetection(confidence=0.91, box=BoundingBox(x_min=10, y_min=20, x_max=110, y_max=220))
    ]


def test_converts_empty_yolo_boxes_to_empty_list() -> None:
    boxes = Boxes(torch.zeros((0, 6)), orig_shape=IMAGE_SHAPE)

    assert convert_boxes_to_book_detections(boxes) == []


def test_finds_class_id_by_name() -> None:
    assert find_class_id({0: "person", 73: "book"}, "book") == 73


@pytest.mark.slow
def test_detector_knows_the_book_class(book_detector: YOLO) -> None:
    assert "book" in book_detector.names.values()


@pytest.mark.slow
def test_detects_no_books_in_blank_image(book_detector: YOLO, blank_image: np.ndarray) -> None:
    assert detect_books(blank_image, book_detector) == []
