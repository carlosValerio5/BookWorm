import easyocr
import numpy as np
import pytest
from image_factories import VALID_ISBN13

from bookworm.isbn_validation import extract_isbn_from_text
from bookworm.scan_types import BoundingBox, RecognizedText
from bookworm.text_recognition import convert_easyocr_output, recognize_text


def test_converts_easyocr_output_to_recognized_text() -> None:
    raw_readings = [([[10, 20], [110, 20], [110, 50], [10, 50]], "ISBN", 0.98766)]

    assert convert_easyocr_output(raw_readings) == [
        RecognizedText(text="ISBN", confidence=0.9877, box=BoundingBox(x_min=10, y_min=20, x_max=110, y_max=50))
    ]


def test_converts_empty_easyocr_output_to_empty_list() -> None:
    assert convert_easyocr_output([]) == []


@pytest.mark.slow
def test_recognizes_isbn_printed_as_text(text_reader: easyocr.Reader, isbn_text_image: np.ndarray) -> None:
    texts = recognize_text(isbn_text_image, text_reader)

    assert extract_isbn_from_text(" ".join(text.text for text in texts)) == VALID_ISBN13
