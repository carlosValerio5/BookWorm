from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum


class ScanKind(StrEnum):
    ISBN = "isbn"
    COVER = "cover"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class BoundingBox:
    x_min: int
    y_min: int
    x_max: int
    y_max: int

    @classmethod
    def from_points(cls, points: Iterable[Sequence[float]]) -> "BoundingBox":
        x_values, y_values = zip(*points)
        return cls(
            x_min=int(min(x_values)),
            y_min=int(min(y_values)),
            x_max=int(max(x_values)),
            y_max=int(max(y_values)),
        )

    def scaled(self, factor: float) -> "BoundingBox":
        return BoundingBox(
            x_min=round(self.x_min * factor),
            y_min=round(self.y_min * factor),
            x_max=round(self.x_max * factor),
            y_max=round(self.y_max * factor),
        )


@dataclass(frozen=True)
class BookDetection:
    confidence: float
    box: BoundingBox


@dataclass(frozen=True)
class IsbnBarcode:
    isbn: str
    box: BoundingBox


@dataclass(frozen=True)
class RecognizedText:
    text: str
    confidence: float
    box: BoundingBox


@dataclass(frozen=True)
class ScanResult:
    scan_id: str
    image_path: str
    kind: ScanKind
    isbn: str | None
    books: list[BookDetection]
    barcodes: list[IsbnBarcode]
    texts: list[RecognizedText]
