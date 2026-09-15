import easyocr
import numpy as np
import pytest
from image_factories import (
    VALID_NON_ISBN_EAN13,
    VALID_ISBN13,
    create_accented_text_image,
    create_blank_image,
    create_ean13_image,
    create_text_image,
)
from ultralytics import YOLO

from bookworm.book_detection import load_book_detector
from bookworm.logging_setup import configure_logging
from bookworm.text_recognition import load_text_reader


@pytest.fixture(autouse=True, scope="session")
def session_logging(tmp_path_factory: pytest.TempPathFactory) -> None:
    configure_logging(tmp_path_factory.mktemp("logs") / "bookworm.jsonl")


@pytest.fixture
def blank_image() -> np.ndarray:
    return create_blank_image()


@pytest.fixture
def isbn_barcode_image() -> np.ndarray:
    return create_ean13_image(VALID_ISBN13)


@pytest.fixture
def non_isbn_barcode_image() -> np.ndarray:
    return create_ean13_image(VALID_NON_ISBN_EAN13)


@pytest.fixture
def isbn_text_image() -> np.ndarray:
    return create_text_image("ISBN 978-0-306-40615-7")


@pytest.fixture
def spanish_title_image() -> np.ndarray:
    return create_accented_text_image("El Buscón")


@pytest.fixture(scope="session")
def book_detector() -> YOLO:
    return load_book_detector()


@pytest.fixture(scope="session")
def text_reader() -> easyocr.Reader:
    return load_text_reader()
