from dataclasses import dataclass
from enum import StrEnum

from bookworm.scan_types import BoundingBox, ScanKind

ANNOTATION_SCHEMA_VERSION = 1


class BoxType(StrEnum):
    BOOK = "book"
    BARCODE = "barcode"
    PRINTED_ISBN = "printed_isbn"
    TITLE = "title"
    AUTHOR = "author"
    PUBLISHER = "publisher"
    OTHER_TEXT = "other_text"


@dataclass(frozen=True)
class LabeledBox:
    box_type: BoxType
    box: BoundingBox
    text: str
    confirmed: bool


@dataclass(frozen=True)
class AnnotationDraft:
    photo_path: str
    photo_width: int
    photo_height: int
    kind: ScanKind
    boxes: list[LabeledBox]
    labeling_duration_ms: int


@dataclass(frozen=True)
class PhotoAnnotation:
    schema_version: int
    saved_at: str
    photo_path: str
    photo_width: int
    photo_height: int
    kind: ScanKind
    boxes: list[LabeledBox]
    labeling_duration_ms: int
