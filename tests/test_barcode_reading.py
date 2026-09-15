import numpy as np
from image_factories import VALID_ISBN13, place_on_white_canvas

from bookworm.barcode_reading import read_isbn_barcodes


def test_reads_isbn_from_barcode(isbn_barcode_image: np.ndarray) -> None:
    barcodes = read_isbn_barcodes(isbn_barcode_image)

    assert [barcode.isbn for barcode in barcodes] == [VALID_ISBN13]


def test_barcode_box_is_inside_image(isbn_barcode_image: np.ndarray) -> None:
    box = read_isbn_barcodes(isbn_barcode_image)[0].box
    image_height, image_width = isbn_barcode_image.shape[:2]

    assert 0 <= box.x_min < box.x_max <= image_width
    assert 0 <= box.y_min < box.y_max <= image_height


def test_barcode_box_follows_barcode_position_in_image(isbn_barcode_image: np.ndarray) -> None:
    shifted_image = place_on_white_canvas(isbn_barcode_image, top=50, left=100)

    box = read_isbn_barcodes(shifted_image)[0].box

    assert box.x_min >= 100
    assert box.y_min >= 50


def test_ignores_barcodes_that_are_not_isbn(non_isbn_barcode_image: np.ndarray) -> None:
    assert read_isbn_barcodes(non_isbn_barcode_image) == []


def test_returns_empty_list_for_image_without_barcodes(blank_image: np.ndarray) -> None:
    assert read_isbn_barcodes(blank_image) == []
