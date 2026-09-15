from pathlib import Path
from uuid import uuid4

import easyocr
import structlog
from ultralytics import YOLO

from bookworm.barcode_reading import read_isbn_barcodes
from bookworm.book_detection import detect_books
from bookworm.image_loading import load_image
from bookworm.isbn_validation import extract_isbn_from_text
from bookworm.logging_setup import log_call
from bookworm.scan_types import BookDetection, IsbnBarcode, RecognizedText, ScanKind, ScanResult
from bookworm.text_recognition import recognize_text

logger = structlog.stdlib.get_logger(__name__)


def scan_image(image_path: Path, book_detector: YOLO, text_reader: easyocr.Reader) -> ScanResult:
    scan_id = uuid4().hex
    with (
        structlog.contextvars.bound_contextvars(scan_id=scan_id),
        log_call(logger, "scan_image", image_path=str(image_path)),
    ):
        image = load_image(image_path)
        barcodes = read_isbn_barcodes(image)
        books = detect_books(image, book_detector)
        texts = recognize_text(image, text_reader)
        isbn = find_isbn(barcodes, texts)
        kind = decide_scan_kind(isbn, books)
        logger.info(
            "scan_classified",
            kind=kind,
            isbn=isbn,
            book_count=len(books),
            barcode_count=len(barcodes),
            text_count=len(texts),
        )
    return ScanResult(
        scan_id=scan_id,
        image_path=str(image_path),
        kind=kind,
        isbn=isbn,
        books=books,
        barcodes=barcodes,
        texts=texts,
    )


def find_isbn(barcodes: list[IsbnBarcode], texts: list[RecognizedText]) -> str | None:
    barcode_isbns = [barcode.isbn for barcode in barcodes]
    text_isbn = extract_isbn_from_text(" ".join(text.text for text in texts))
    return next((isbn for isbn in [*barcode_isbns, text_isbn] if isbn is not None), None)


def decide_scan_kind(isbn: str | None, books: list[BookDetection]) -> ScanKind:
    if isbn is not None:
        return ScanKind.ISBN
    if books:
        return ScanKind.COVER
    return ScanKind.UNKNOWN
