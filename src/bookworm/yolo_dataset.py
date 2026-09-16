import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import structlog
import yaml

from bookworm.annotator.annotation_storage import annotation_path_for, list_photo_paths, load_annotation
from bookworm.annotator.annotation_types import BoxType, PhotoAnnotation
from bookworm.image_loading import load_image
from bookworm.logging_setup import log_call
from bookworm.scan_types import BoundingBox

logger = structlog.stdlib.get_logger(__name__)

CLASS_NAMES = list(BoxType)
VAL_SPLIT_FRACTION = 0.15
DatasetSplit = Literal["train", "val"]


@dataclass(frozen=True)
class YoloDatasetSummary:
    train_count: int
    val_count: int
    skipped_unlabeled_count: int
    output_dir: str
    data_yaml_path: str


def assign_split(photo_path: str) -> DatasetSplit:
    digest = hashlib.sha256(photo_path.encode()).digest()
    return "val" if digest[0] / 255 < VAL_SPLIT_FRACTION else "train"


def convert_box_to_yolo_line(box_type: BoxType, box: BoundingBox, photo_width: int, photo_height: int) -> str:
    class_id = CLASS_NAMES.index(box_type)
    x_center = (box.x_min + box.x_max) / 2 / photo_width
    y_center = (box.y_min + box.y_max) / 2 / photo_height
    width = (box.x_max - box.x_min) / photo_width
    height = (box.y_max - box.y_min) / photo_height
    return f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}"


def build_yolo_labels_text(annotation: PhotoAnnotation) -> str:
    lines = [
        convert_box_to_yolo_line(labeled_box.box_type, labeled_box.box, annotation.photo_width, annotation.photo_height)
        for labeled_box in annotation.boxes
        if labeled_box.confirmed
    ]
    return "".join(f"{line}\n" for line in lines)


def build_dataset_file_stem(photo_path: str) -> str:
    return photo_path.replace("/", "__")


def write_data_yaml(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    data_yaml_path = output_dir / "data.yaml"
    data_yaml_path.write_text(
        yaml.safe_dump(
            {
                "path": str(output_dir.resolve()),
                "train": "images/train",
                "val": "images/val",
                "names": {index: box_type.value for index, box_type in enumerate(CLASS_NAMES)},
            },
            sort_keys=False,
        )
    )
    return data_yaml_path


def write_photo_into_split(photos_dir: Path, photo_path: str, output_dir: Path, split: DatasetSplit) -> str:
    file_stem = build_dataset_file_stem(Path(photo_path).with_suffix("").as_posix())
    images_split_dir = output_dir / "images" / split
    images_split_dir.mkdir(parents=True, exist_ok=True)
    image_path = images_split_dir / f"{file_stem}.jpg"
    cv2.imwrite(str(image_path), load_image(photos_dir / photo_path))
    return file_stem


def write_labels_into_split(output_dir: Path, split: DatasetSplit, file_stem: str, annotation: PhotoAnnotation) -> None:
    labels_split_dir = output_dir / "labels" / split
    labels_split_dir.mkdir(parents=True, exist_ok=True)
    (labels_split_dir / f"{file_stem}.txt").write_text(build_yolo_labels_text(annotation))


def build_yolo_dataset(photos_dir: Path, labels_dir: Path, output_dir: Path) -> YoloDatasetSummary:
    """Convert every labeled photo in photos_dir into a YOLO training dataset under output_dir.

    Photos with no saved annotation are skipped, not errored - labeling is incremental.
    """
    with log_call(logger, "build_yolo_dataset", photos_dir=str(photos_dir), labels_dir=str(labels_dir), output_dir=str(output_dir)):
        split_counts: dict[DatasetSplit, int] = {"train": 0, "val": 0}
        skipped_unlabeled_count = 0
        for photo_path in list_photo_paths(photos_dir):
            annotation_path = annotation_path_for(labels_dir, photo_path)
            if not annotation_path.is_file():
                skipped_unlabeled_count += 1
                continue
            annotation = load_annotation(annotation_path)
            split = assign_split(photo_path)
            file_stem = write_photo_into_split(photos_dir, photo_path, output_dir, split)
            write_labels_into_split(output_dir, split, file_stem, annotation)
            split_counts[split] += 1
        data_yaml_path = write_data_yaml(output_dir)
        logger.info(
            "yolo_dataset_built",
            train_count=split_counts["train"],
            val_count=split_counts["val"],
            skipped_unlabeled_count=skipped_unlabeled_count,
        )
    return YoloDatasetSummary(
        train_count=split_counts["train"],
        val_count=split_counts["val"],
        skipped_unlabeled_count=skipped_unlabeled_count,
        output_dir=str(output_dir),
        data_yaml_path=str(data_yaml_path),
    )
