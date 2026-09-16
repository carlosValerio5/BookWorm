from datetime import UTC, datetime
from pathlib import Path

import cv2
import yaml
from image_factories import create_blank_image, write_heic_image, write_image

from bookworm.annotator.annotation_storage import build_photo_annotation, save_annotation
from bookworm.annotator.annotation_types import AnnotationDraft, BoxType, LabeledBox
from bookworm.scan_types import BoundingBox, ScanKind
from bookworm.yolo_dataset import assign_split, build_yolo_dataset, convert_box_to_yolo_line

SAVED_AT = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)


def build_annotation(photo_path: str, boxes: list[LabeledBox], photo_width: int = 400, photo_height: int = 200):
    draft = AnnotationDraft(
        photo_path=photo_path,
        photo_width=photo_width,
        photo_height=photo_height,
        kind=ScanKind.COVER,
        boxes=boxes,
        labeling_duration_ms=1000,
    )
    return build_photo_annotation(draft, SAVED_AT)


def test_assign_split_is_deterministic() -> None:
    assert assign_split("cover/IMG_0012.jpg") == assign_split("cover/IMG_0012.jpg")


def test_assign_split_produces_both_train_and_val() -> None:
    splits = {assign_split(f"photo_{index}.jpg") for index in range(50)}
    assert splits == {"train", "val"}


def test_convert_box_to_yolo_line_normalizes_to_photo_dimensions() -> None:
    box = BoundingBox(x_min=100, y_min=50, x_max=300, y_max=150)

    line = convert_box_to_yolo_line(BoxType.TITLE, box, photo_width=400, photo_height=200)

    assert line == "3 0.500000 0.500000 0.500000 0.500000"


def test_build_yolo_dataset_skips_photos_with_no_annotation(tmp_path: Path) -> None:
    photos_dir = tmp_path / "photos"
    labels_dir = tmp_path / "labels"
    output_dir = tmp_path / "yolo"
    photos_dir.mkdir()
    write_image(photos_dir / "unlabeled.jpg", create_blank_image())

    summary = build_yolo_dataset(photos_dir, labels_dir, output_dir)

    assert summary.skipped_unlabeled_count == 1
    assert summary.train_count == 0
    assert summary.val_count == 0


def test_build_yolo_dataset_writes_image_and_label_in_the_assigned_split(tmp_path: Path) -> None:
    photos_dir = tmp_path / "photos"
    labels_dir = tmp_path / "labels"
    output_dir = tmp_path / "yolo"
    photos_dir.mkdir()
    photo_path = "cover.jpg"
    write_image(photos_dir / photo_path, create_blank_image(height=200, width=400))
    box = LabeledBox(box_type=BoxType.BOOK, box=BoundingBox(0, 0, 400, 200), text="", confirmed=True)
    save_annotation(labels_dir, build_annotation(photo_path, [box]))

    summary = build_yolo_dataset(photos_dir, labels_dir, output_dir)

    split = assign_split(photo_path)
    assert (output_dir / "images" / split / "cover.jpg").is_file()
    label_lines = (output_dir / "labels" / split / "cover.txt").read_text().strip().splitlines()
    assert label_lines == ["0 0.500000 0.500000 1.000000 1.000000"]
    assert summary.skipped_unlabeled_count == 0
    assert summary.train_count + summary.val_count == 1


def test_build_yolo_dataset_drops_unconfirmed_boxes(tmp_path: Path) -> None:
    photos_dir = tmp_path / "photos"
    labels_dir = tmp_path / "labels"
    output_dir = tmp_path / "yolo"
    photos_dir.mkdir()
    photo_path = "cover.jpg"
    write_image(photos_dir / photo_path, create_blank_image(height=200, width=400))
    confirmed_box = LabeledBox(box_type=BoxType.BOOK, box=BoundingBox(0, 0, 400, 200), text="", confirmed=True)
    draft_box = LabeledBox(box_type=BoxType.TITLE, box=BoundingBox(10, 10, 50, 50), text="x", confirmed=False)
    save_annotation(labels_dir, build_annotation(photo_path, [confirmed_box, draft_box]))

    build_yolo_dataset(photos_dir, labels_dir, output_dir)

    split = assign_split(photo_path)
    label_lines = (output_dir / "labels" / split / "cover.txt").read_text().strip().splitlines()
    assert len(label_lines) == 1
    assert label_lines[0].startswith("0 ")


def test_build_yolo_dataset_converts_heic_photos_to_jpeg(tmp_path: Path) -> None:
    photos_dir = tmp_path / "photos"
    labels_dir = tmp_path / "labels"
    output_dir = tmp_path / "yolo"
    photos_dir.mkdir()
    photo_path = "cover.HEIC"
    write_heic_image(photos_dir / photo_path, create_blank_image(height=200, width=400))
    box = LabeledBox(box_type=BoxType.BOOK, box=BoundingBox(0, 0, 400, 200), text="", confirmed=True)
    save_annotation(labels_dir, build_annotation(photo_path, [box]))

    build_yolo_dataset(photos_dir, labels_dir, output_dir)

    split = assign_split(photo_path)
    output_image_path = output_dir / "images" / split / "cover.jpg"
    assert output_image_path.is_file()
    assert cv2.imread(str(output_image_path)) is not None


def test_build_yolo_dataset_writes_data_yaml_with_class_names_in_enum_order(tmp_path: Path) -> None:
    photos_dir = tmp_path / "photos"
    labels_dir = tmp_path / "labels"
    output_dir = tmp_path / "yolo"
    photos_dir.mkdir()

    summary = build_yolo_dataset(photos_dir, labels_dir, output_dir)

    data_yaml = yaml.safe_load(Path(summary.data_yaml_path).read_text())
    assert data_yaml["names"] == {
        0: "book",
        1: "barcode",
        2: "printed_isbn",
        3: "title",
        4: "author",
        5: "publisher",
        6: "other_text",
    }
    assert data_yaml["train"] == "images/train"
    assert data_yaml["val"] == "images/val"
