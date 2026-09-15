from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import structlog
from pydantic import TypeAdapter

from bookworm.annotator.annotation_types import (
    ANNOTATION_SCHEMA_VERSION,
    AnnotationDraft,
    BoxType,
    LabeledBox,
    PhotoAnnotation,
)
from bookworm.isbn_validation import extract_isbn_from_text
from bookworm.logging_setup import log_call
from bookworm.scan_types import BoundingBox

logger = structlog.stdlib.get_logger(__name__)

PHOTO_FILE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".heic", ".heif"})
ANNOTATION_FILE_SUFFIX = ".json"
PHOTO_ANNOTATION_ADAPTER = TypeAdapter(PhotoAnnotation)


class PhotoPathError(Exception):
    pass


class PhotoNotFoundError(Exception):
    pass


class AnnotationNotFoundError(Exception):
    pass


class AnnotationProblemsError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


def accepts_any_text(_text: str) -> bool:
    return True


def has_no_text(text: str) -> bool:
    return text == ""


def has_visible_text(text: str) -> bool:
    return text.strip() != ""


def contains_valid_isbn(text: str) -> bool:
    return extract_isbn_from_text(text) is not None


BOX_TEXT_RULES: dict[BoxType, tuple[Callable[[str], bool], str]] = {
    BoxType.BOOK: (accepts_any_text, ""),
    BoxType.BARCODE: (has_no_text, "must not have text"),
    BoxType.PRINTED_ISBN: (contains_valid_isbn, "text {text!r} has no valid ISBN"),
    BoxType.TITLE: (has_visible_text, "needs text"),
    BoxType.AUTHOR: (has_visible_text, "needs text"),
    BoxType.PUBLISHER: (has_visible_text, "needs text"),
    BoxType.OTHER_TEXT: (has_visible_text, "needs text"),
}


def list_photo_paths(photos_dir: Path) -> list[str]:
    return sorted(
        file_path.relative_to(photos_dir).as_posix()
        for file_path in photos_dir.rglob("*")
        if is_visible_photo_file(photos_dir, file_path)
    )


def is_visible_photo_file(photos_dir: Path, file_path: Path) -> bool:
    is_hidden = any(part.startswith(".") for part in file_path.relative_to(photos_dir).parts)
    return file_path.is_file() and not is_hidden and file_path.suffix.lower() in PHOTO_FILE_SUFFIXES


def resolve_photo_path(photos_dir: Path, photo_path: str) -> Path:
    resolved_photos_dir = photos_dir.resolve()
    resolved_photo_path = (resolved_photos_dir / photo_path).resolve()
    if not resolved_photo_path.is_relative_to(resolved_photos_dir):
        raise PhotoPathError(f"Photo path {photo_path!r} is outside {photos_dir}")
    return resolved_photo_path


def find_photo_file(photos_dir: Path, photo_path: str) -> Path:
    photo_file = resolve_photo_path(photos_dir, photo_path)
    if not photo_file.is_file():
        raise PhotoNotFoundError(f"No photo at {photo_path!r} in {photos_dir}")
    return photo_file


def annotation_path_for(labels_dir: Path, photo_path: str) -> Path:
    return labels_dir / f"{photo_path}{ANNOTATION_FILE_SUFFIX}"


def find_annotation_file(labels_dir: Path, photo_path: str) -> Path:
    annotation_path = annotation_path_for(labels_dir, photo_path)
    if not annotation_path.is_file():
        raise AnnotationNotFoundError(f"No annotation for {photo_path!r} in {labels_dir}")
    return annotation_path


def count_saved_boxes(labels_dir: Path, photo_path: str) -> int:
    annotation_path = annotation_path_for(labels_dir, photo_path)
    return len(load_annotation(annotation_path).boxes) if annotation_path.is_file() else 0


def describe_photo(labels_dir: Path, photo_path: str) -> dict[str, str | bool | int]:
    return {
        "photo_path": photo_path,
        "annotated": annotation_path_for(labels_dir, photo_path).is_file(),
        "box_count": count_saved_boxes(labels_dir, photo_path),
    }


def build_photo_annotation(draft: AnnotationDraft, saved_at_utc: datetime) -> PhotoAnnotation:
    return PhotoAnnotation(
        schema_version=ANNOTATION_SCHEMA_VERSION,
        saved_at=saved_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        photo_path=draft.photo_path,
        photo_width=draft.photo_width,
        photo_height=draft.photo_height,
        kind=draft.kind,
        boxes=draft.boxes,
        labeling_duration_ms=draft.labeling_duration_ms,
    )


def save_annotation(labels_dir: Path, annotation: PhotoAnnotation) -> Path:
    annotation_path = annotation_path_for(labels_dir, annotation.photo_path)
    with log_call(logger, "save_annotation", annotation_path=str(annotation_path)):
        annotation_path.parent.mkdir(parents=True, exist_ok=True)
        write_file_atomically(annotation_path, PHOTO_ANNOTATION_ADAPTER.dump_json(annotation, indent=2))
    return annotation_path


def write_file_atomically(file_path: Path, content: bytes) -> None:
    temporary_path = file_path.with_name(f"{file_path.name}.tmp")
    temporary_path.write_bytes(content)
    temporary_path.replace(file_path)


def load_annotation(annotation_path: Path) -> PhotoAnnotation:
    with log_call(logger, "load_annotation", annotation_path=str(annotation_path)):
        return PHOTO_ANNOTATION_ADAPTER.validate_json(annotation_path.read_bytes())


def find_annotation_problems(draft: AnnotationDraft) -> list[str]:
    return [
        problem
        for box_index, labeled_box in enumerate(draft.boxes)
        for problem in find_box_problems(box_index, labeled_box, draft.photo_width, draft.photo_height)
    ]


def find_box_problems(box_index: int, labeled_box: LabeledBox, photo_width: int, photo_height: int) -> list[str]:
    is_text_valid, text_problem = BOX_TEXT_RULES[labeled_box.box_type]
    box_label = f"box {box_index} ({labeled_box.box_type})"
    checks = [
        (
            is_box_inside_photo(labeled_box.box, photo_width, photo_height),
            f"{box_label} is outside the {photo_width}x{photo_height} photo",
        ),
        (has_area(labeled_box.box), f"{box_label} has no area"),
        (is_text_valid(labeled_box.text), f"{box_label} {text_problem.format(text=labeled_box.text)}"),
    ]
    return [problem for check_passed, problem in checks if not check_passed]


def is_box_inside_photo(box: BoundingBox, photo_width: int, photo_height: int) -> bool:
    return box.x_min >= 0 and box.y_min >= 0 and box.x_max <= photo_width and box.y_max <= photo_height


def has_area(box: BoundingBox) -> bool:
    return box.x_min < box.x_max and box.y_min < box.y_max


def raise_for_annotation_problems(problems: list[str]) -> None:
    if problems:
        raise AnnotationProblemsError(problems)
