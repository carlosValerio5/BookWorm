import numpy as np
import structlog
import zxingcpp

from bookworm.isbn_validation import is_isbn_barcode
from bookworm.logging_setup import log_call
from bookworm.scan_types import BoundingBox, IsbnBarcode

logger = structlog.stdlib.get_logger(__name__)


def read_isbn_barcodes(image: np.ndarray) -> list[IsbnBarcode]:
    with log_call(logger, "read_isbn_barcodes"):
        raw_barcodes = zxingcpp.read_barcodes(image, formats=zxingcpp.BarcodeFormat.EAN13)
        isbn_barcodes = [convert_to_isbn_barcode(barcode) for barcode in raw_barcodes if is_isbn_barcode(barcode.text)]
        logger.info(
            "isbn_barcodes_read",
            raw_barcode_texts=[barcode.text for barcode in raw_barcodes],
            isbns=[barcode.isbn for barcode in isbn_barcodes],
        )
    return isbn_barcodes


def convert_to_isbn_barcode(barcode: zxingcpp.Barcode) -> IsbnBarcode:
    position = barcode.position
    corners = [position.top_left, position.top_right, position.bottom_right, position.bottom_left]
    return IsbnBarcode(isbn=barcode.text, box=BoundingBox.from_points((corner.x, corner.y) for corner in corners))
