import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bookworm.annotator.annotation_storage import (
    PhotoPathError,
    annotation_path_for,
    build_photo_annotation,
    find_annotation_problems,
    list_photo_paths,
    load_annotation,
    resolve_photo_path,
    save_annotation,
)
from bookworm.annotator.annotation_types import AnnotationDraft, BoxType, LabeledBox
from bookworm.scan_types import BoundingBox, ScanKind

VALID_BOX = BoundingBox(x_min=10, y_min=20, x_max=200, y_max=80)
SAVED_AT = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)


def build_labeled_box(box_type: BoxType = BoxType.TITLE, text: str = "El Buscón", box: BoundingBox = VALID_BOX) -> LabeledBox:
    return LabeledBox(box_type=box_type, box=box, text=text, confirmed=True)


def build_draft(boxes: list[LabeledBox]) -> AnnotationDraft:
    return AnnotationDraft(
        photo_path="cover/IMG_0012.HEIC",
        photo_width=400,
        photo_height=300,
        kind=ScanKind.COVER,
        boxes=boxes,
        labeling_duration_ms=41250,
    )


def create_empty_files(root: Path, relative_paths: list[str]) -> None:
    for relative_path in relative_paths:
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()


def test_list_photo_paths_finds_photos_recursively_sorted_and_skips_other_files(tmp_path: Path) -> None:
    create_empty_files(
        tmp_path,
        ["isbn/c.png", "cover/b.HEIC", "a.jpg", "d.jpeg", "e.heif", "notes.txt", ".hidden.jpg", "cover/.DS_Store"],
    )

    assert list_photo_paths(tmp_path) == ["a.jpg", "cover/b.HEIC", "d.jpeg", "e.heif", "isbn/c.png"]


def test_resolve_photo_path_returns_file_inside_photos_folder(tmp_path: Path) -> None:
    assert resolve_photo_path(tmp_path, "cover/b.HEIC") == (tmp_path / "cover" / "b.HEIC").resolve()


@pytest.mark.parametrize("photo_path", ["../outside.jpg", "cover/../../outside.jpg", "/etc/passwd"])
def test_resolve_photo_path_rejects_paths_outside_photos_folder(tmp_path: Path, photo_path: str) -> None:
    with pytest.raises(PhotoPathError):
        resolve_photo_path(tmp_path / "photos", photo_path)


def test_annotation_path_mirrors_photo_path_and_keeps_its_suffix(tmp_path: Path) -> None:
    assert annotation_path_for(tmp_path, "cover/IMG_0012.HEIC") == tmp_path / "cover" / "IMG_0012.HEIC.json"


def test_build_photo_annotation_stamps_schema_version_and_utc_time() -> None:
    annotation = build_photo_annotation(build_draft([build_labeled_box()]), SAVED_AT)

    assert annotation.schema_version == 1
    assert annotation.saved_at == "2026-09-15T08:00:00Z"
    assert annotation.boxes == [build_labeled_box()]


def test_saved_annotation_loads_back_unchanged(tmp_path: Path) -> None:
    annotation = build_photo_annotation(build_draft([build_labeled_box()]), SAVED_AT)

    annotation_path = save_annotation(tmp_path, annotation)

    assert annotation_path == tmp_path / "cover" / "IMG_0012.HEIC.json"
    assert load_annotation(annotation_path) == annotation


def test_saved_annotation_is_readable_utf8_json_without_leftover_files(tmp_path: Path) -> None:
    annotation_path = save_annotation(tmp_path, build_photo_annotation(build_draft([build_labeled_box()]), SAVED_AT))

    saved_text = annotation_path.read_text(encoding="utf-8")
    saved_json = json.loads(saved_text)
    assert "El Buscón" in saved_text
    assert saved_json["kind"] == "cover"
    assert saved_json["boxes"][0]["box_type"] == "title"
    assert saved_json["boxes"][0]["box"] == {"x_min": 10, "y_min": 20, "x_max": 200, "y_max": 80}
    assert [path.name for path in annotation_path.parent.iterdir()] == ["IMG_0012.HEIC.json"]


def test_valid_draft_has_no_problems() -> None:
    boxes = [
        build_labeled_box(BoxType.BOOK, text=""),
        build_labeled_box(BoxType.BARCODE, text=""),
        build_labeled_box(BoxType.PRINTED_ISBN, text="ISBN 978-0-306-40615-7"),
        build_labeled_box(BoxType.TITLE, text="El Buscón"),
        build_labeled_box(BoxType.AUTHOR, text="Quevedo"),
        build_labeled_box(BoxType.PUBLISHER, text="Castalia"),
        build_labeled_box(BoxType.OTHER_TEXT, text="Clásicos"),
        build_labeled_box(box=BoundingBox(x_min=0, y_min=0, x_max=400, y_max=300)),
    ]

    assert find_annotation_problems(build_draft(boxes)) == []


@pytest.mark.parametrize(
    ("labeled_box", "expected_problem"),
    [
        (
            build_labeled_box(box=BoundingBox(x_min=-1, y_min=20, x_max=200, y_max=80)),
            "box 0 (title) is outside the 400x300 photo",
        ),
        (
            build_labeled_box(box=BoundingBox(x_min=10, y_min=20, x_max=401, y_max=80)),
            "box 0 (title) is outside the 400x300 photo",
        ),
        (
            build_labeled_box(box=BoundingBox(x_min=10, y_min=20, x_max=200, y_max=301)),
            "box 0 (title) is outside the 400x300 photo",
        ),
        (
            build_labeled_box(box=BoundingBox(x_min=200, y_min=20, x_max=200, y_max=80)),
            "box 0 (title) has no area",
        ),
        (
            build_labeled_box(box=BoundingBox(x_min=10, y_min=80, x_max=200, y_max=20)),
            "box 0 (title) has no area",
        ),
        (
            build_labeled_box(BoxType.BARCODE, text="9780306406157"),
            "box 0 (barcode) must not have text",
        ),
        (
            build_labeled_box(BoxType.PRINTED_ISBN, text="ISBN 123"),
            "box 0 (printed_isbn) text 'ISBN 123' has no valid ISBN",
        ),
        (build_labeled_box(BoxType.TITLE, text="  "), "box 0 (title) needs text"),
        (build_labeled_box(BoxType.AUTHOR, text=""), "box 0 (author) needs text"),
        (build_labeled_box(BoxType.PUBLISHER, text=""), "box 0 (publisher) needs text"),
        (build_labeled_box(BoxType.OTHER_TEXT, text=""), "box 0 (other_text) needs text"),
    ],
)
def test_find_annotation_problems_reports_bad_box(labeled_box: LabeledBox, expected_problem: str) -> None:
    assert find_annotation_problems(build_draft([labeled_box])) == [expected_problem]


def test_find_annotation_problems_reports_every_problem_with_its_box_index() -> None:
    boxes = [
        build_labeled_box(),
        build_labeled_box(BoxType.BARCODE, text="123", box=BoundingBox(x_min=10, y_min=20, x_max=500, y_max=80)),
    ]

    assert find_annotation_problems(build_draft(boxes)) == [
        "box 1 (barcode) is outside the 400x300 photo",
        "box 1 (barcode) must not have text",
    ]
