from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import structlog
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from bookworm.annotator.annotation_storage import (
    AnnotationNotFoundError,
    AnnotationProblemsError,
    PhotoNotFoundError,
    PhotoPathError,
    build_photo_annotation,
    describe_photo,
    find_annotation_file,
    find_annotation_problems,
    find_photo_file,
    list_photo_paths,
    load_annotation,
    raise_for_annotation_problems,
    resolve_photo_path,
    save_annotation,
)
from bookworm.annotator.annotation_types import AnnotationDraft, BoxType, LabeledBox, PhotoAnnotation
from bookworm.book_detection import detect_books, load_book_detector
from bookworm.image_loading import ImageLoadError, load_image
from bookworm.isbn_validation import extract_isbn_from_text
from bookworm.logging_setup import log_call
from bookworm.scan_types import BookDetection, ScanResult

logger = structlog.stdlib.get_logger(__name__)

STATIC_DIRECTORY = Path(__file__).parent / "static"
JPEG_QUALITY = 90


class ImageEncodeError(Exception):
    pass


def create_annotator_app(photos_dir: Path, labels_dir: Path) -> FastAPI:
    app = FastAPI(title="BookWorm Annotator")
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")
    add_error_responses(app)

    @app.get("/")
    def show_annotator_page() -> FileResponse:
        return FileResponse(STATIC_DIRECTORY / "index.html")

    @app.get("/api/photos")
    def list_photos() -> list[dict[str, str | bool | int]]:
        with log_call(logger, "list_photos", photos_dir=str(photos_dir), labels_dir=str(labels_dir)):
            return [describe_photo(labels_dir, photo_path) for photo_path in list_photo_paths(photos_dir)]

    @app.get("/api/image")
    def get_photo_image(photo: str) -> Response:
        photo_file = find_photo_file(photos_dir, photo)
        with log_call(logger, "get_photo_image", photo_path=photo):
            jpeg_bytes = encode_jpeg(load_image(photo_file))
        return Response(content=jpeg_bytes, media_type="image/jpeg")

    @app.get("/api/detections")
    def get_photo_detections(photo: str) -> list[BookDetection]:
        photo_file = find_photo_file(photos_dir, photo)
        with log_call(logger, "get_photo_detections", photo_path=photo):
            return detect_books(load_image(photo_file), load_book_detector())

    @app.get("/api/annotation")
    def get_photo_annotation(photo: str) -> PhotoAnnotation:
        resolve_photo_path(photos_dir, photo)
        return load_annotation(find_annotation_file(labels_dir, photo))

    @app.put("/api/annotation")
    def save_photo_annotation(draft: AnnotationDraft) -> PhotoAnnotation:
        find_photo_file(photos_dir, draft.photo_path)
        raise_for_annotation_problems(find_annotation_problems(draft))
        with log_call(logger, "save_photo_annotation", photo_path=draft.photo_path):
            annotation = build_photo_annotation(draft, datetime.now(UTC))
            save_annotation(labels_dir, annotation)
            logger.info(
                "annotation_saved",
                photo_path=annotation.photo_path,
                kind=annotation.kind,
                box_count=len(annotation.boxes),
                box_type_counts=count_box_types(annotation.boxes),
                labeling_duration_ms=annotation.labeling_duration_ms,
            )
        return annotation

    return app


def encode_jpeg(image: np.ndarray) -> bytes:
    was_encoded, jpeg_buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    if not was_encoded:
        raise ImageEncodeError("Could not encode the photo as JPEG")
    return jpeg_buffer.tobytes()


def box_type_for_recognized_text(text: str) -> BoxType:
    return BoxType.PRINTED_ISBN if extract_isbn_from_text(text) is not None else BoxType.OTHER_TEXT


def labeled_boxes_from_scan(scan_result: ScanResult) -> list[LabeledBox]:
    book_boxes = [LabeledBox(box_type=BoxType.BOOK, box=book.box, text="", confirmed=False) for book in scan_result.books]
    barcode_boxes = [
        LabeledBox(box_type=BoxType.BARCODE, box=barcode.box, text="", confirmed=False) for barcode in scan_result.barcodes
    ]
    text_boxes = [
        LabeledBox(box_type=box_type_for_recognized_text(text.text), box=text.box, text=text.text, confirmed=False)
        for text in scan_result.texts
    ]
    return [*book_boxes, *barcode_boxes, *text_boxes]


def count_box_types(boxes: list[LabeledBox]) -> dict[str, int]:
    return dict(Counter(str(labeled_box.box_type) for labeled_box in boxes))


def add_error_responses(app: FastAPI) -> None:
    app.add_exception_handler(PhotoPathError, build_detail_response_handler(400))
    app.add_exception_handler(PhotoNotFoundError, build_detail_response_handler(404))
    app.add_exception_handler(AnnotationNotFoundError, build_detail_response_handler(404))
    app.add_exception_handler(ImageLoadError, build_detail_response_handler(422))
    app.add_exception_handler(AnnotationProblemsError, respond_with_annotation_problems)
    app.add_exception_handler(RequestValidationError, respond_with_request_validation_errors)


def log_rejected_request(request: Request, status_code: int, error: Exception) -> None:
    logger.warning(
        "request_rejected",
        method=request.method,
        path=request.url.path,
        query=request.url.query,
        status_code=status_code,
        error=type(error).__name__,
        detail=str(error),
    )


def build_detail_response_handler(status_code: int) -> Callable[[Request, Exception], JSONResponse]:
    def respond_with_detail(request: Request, error: Exception) -> JSONResponse:
        log_rejected_request(request, status_code, error)
        return JSONResponse(status_code=status_code, content={"detail": str(error)})

    return respond_with_detail


def respond_with_annotation_problems(request: Request, error: AnnotationProblemsError) -> JSONResponse:
    log_rejected_request(request, 422, error)
    return JSONResponse(status_code=422, content={"problems": error.problems})


async def respond_with_request_validation_errors(request: Request, error: RequestValidationError) -> Response:
    log_rejected_request(request, 422, error)
    return await request_validation_exception_handler(request, error)
