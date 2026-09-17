import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import cv2
import numpy as np
import structlog
import typer
import uvicorn

from bookworm.annotation_drawing import draw_scan_result
from bookworm.annotator.web_app import create_annotator_app
from bookworm.book_detection import load_book_detector
from bookworm.drive_download import DriveDownloadError, download_drive_folder
from bookworm.image_loading import load_image
from bookworm.logging_setup import configure_logging, log_call
from bookworm.mobile.server import create_mobile_app
from bookworm.scan_classification import scan_image
from bookworm.scan_types import ScanResult
from bookworm.text_recognition import load_text_reader
from bookworm.training_dashboard.web_app import create_dashboard_app
from bookworm.yolo_dataset import build_yolo_dataset
from bookworm.yolo_training import DEFAULT_BASE_WEIGHTS
from bookworm.yolo_training import DEFAULT_BATCH_SIZE as DEFAULT_TRAINING_BATCH_SIZE
from bookworm.yolo_training import DEFAULT_EPOCHS as DEFAULT_TRAINING_EPOCHS
from bookworm.yolo_training import DEFAULT_IMAGE_SIZE as DEFAULT_TRAINING_IMAGE_SIZE
from bookworm.yolo_training import run_yolo_fine_tune

logger = structlog.stdlib.get_logger(__name__)

app = typer.Typer(no_args_is_help=True, help="Scan a book photo and tell if it shows a cover or an ISBN.")

ExistingImagePath = Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)]
ExistingDirectoryPath = Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True)]

ANNOTATOR_HOST = "127.0.0.1"
MOBILE_API_HOST = "0.0.0.0"
DEFAULT_ANNOTATOR_PORT = 8765
DEFAULT_DASHBOARD_PORT = 8766
DEFAULT_MOBILE_PORT = 8000
DEFAULT_LABELS_DIRECTORY = Path("labels")
DEFAULT_DRIVE_OUTPUT_DIR = Path("dataset/drive")
DEFAULT_MOBILE_PHOTOS_DIR = Path("dataset/photos")
DEFAULT_YOLO_DATASET_DIR = Path("dataset/yolo")
DEFAULT_RUNS_DIRECTORY = Path("runs")


class ImageWriteError(Exception):
    pass


@app.command()
def scan(image_path: ExistingImagePath) -> None:
    """Print the scan result as JSON."""
    scan_result = scan_image(image_path, load_book_detector(), load_text_reader())
    typer.echo(format_scan_result_as_json(scan_result))


@app.command()
def annotate(image_path: ExistingImagePath, output_path: Path) -> None:
    """Save a copy of the image with the boxes drawn, then print the scan result as JSON."""
    scan_result = scan_image(image_path, load_book_detector(), load_text_reader())
    write_annotated_image(output_path, draw_scan_result(load_image(image_path), scan_result))
    typer.echo(format_scan_result_as_json(scan_result))


@app.command()
def annotator(
    photos_dir: ExistingDirectoryPath,
    labels_dir: Annotated[Path, typer.Option(help="Folder where labels are saved.")] = DEFAULT_LABELS_DIRECTORY,
    port: Annotated[int, typer.Option(help="Port for the local web app.")] = DEFAULT_ANNOTATOR_PORT,
) -> None:
    """Open the local web app for labeling book photos by hand."""
    logger.info(
        "annotator_starting",
        photos_dir=str(photos_dir),
        labels_dir=str(labels_dir),
        url=f"http://{ANNOTATOR_HOST}:{port}",
    )
    uvicorn.run(create_annotator_app(photos_dir, labels_dir), host=ANNOTATOR_HOST, port=port, log_config=None)


@app.command()
def dashboard(
    runs_dir: Annotated[Path, typer.Option(help="Folder with YOLO training runs.")] = DEFAULT_RUNS_DIRECTORY,
    port: Annotated[int, typer.Option(help="Port for the local web app.")] = DEFAULT_DASHBOARD_PORT,
) -> None:
    """Open a local web app showing live loss and validation accuracy for the latest training run."""
    logger.info("dashboard_starting", runs_dir=str(runs_dir), url=f"http://{ANNOTATOR_HOST}:{port}")
    uvicorn.run(create_dashboard_app(runs_dir), host=ANNOTATOR_HOST, port=port, log_config=None)


@app.command()
def serve(
    photos_dir: Annotated[Path, typer.Option(help="Folder where scanned photos are saved.")] = DEFAULT_MOBILE_PHOTOS_DIR,
    port: Annotated[int, typer.Option(help="Port for the mobile API.")] = DEFAULT_MOBILE_PORT,
) -> None:
    """Serve the BookWorm Mobile API for the phone app to scan and live-detect against."""
    logger.info("mobile_api_starting", photos_dir=str(photos_dir), url=f"http://{MOBILE_API_HOST}:{port}")
    uvicorn.run(create_mobile_app(photos_dir), host=MOBILE_API_HOST, port=port, log_config=None)


@app.command(name="fetch-drive")
def fetch_drive(
    folder_url: str,
    output_dir: Annotated[Path, typer.Option(help="Folder where downloaded photos are saved.")] = DEFAULT_DRIVE_OUTPUT_DIR,
) -> None:
    """Download every photo in a public Google Drive folder, ready for the annotator."""
    try:
        downloaded_file_paths = download_drive_folder(folder_url, output_dir)
    except DriveDownloadError as error:
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps({"downloaded": len(downloaded_file_paths), "output_dir": str(output_dir)}))


@app.command(name="build-yolo-dataset")
def build_yolo_dataset_command(
    photos_dir: ExistingDirectoryPath,
    labels_dir: Annotated[Path, typer.Option(help="Folder with saved annotator labels.")] = DEFAULT_LABELS_DIRECTORY,
    output_dir: Annotated[Path, typer.Option(help="Folder to write the YOLO dataset into.")] = DEFAULT_YOLO_DATASET_DIR,
) -> None:
    """Convert labeled photos into a YOLO training dataset."""
    summary = build_yolo_dataset(photos_dir, labels_dir, output_dir)
    typer.echo(json.dumps(asdict(summary)))


@app.command(name="train-yolo")
def train_yolo(
    dataset_yaml: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    base_weights: Annotated[Path, typer.Option(help="Pretrained weights to fine-tune from.")] = DEFAULT_BASE_WEIGHTS,
    epochs: Annotated[int, typer.Option(min=1)] = DEFAULT_TRAINING_EPOCHS,
    imgsz: Annotated[int, typer.Option(min=1)] = DEFAULT_TRAINING_IMAGE_SIZE,
    batch: Annotated[int, typer.Option(min=1)] = DEFAULT_TRAINING_BATCH_SIZE,
) -> None:
    """Fine-tune the book detector on a YOLO dataset built by build-yolo-dataset."""
    best_weights_path = run_yolo_fine_tune(dataset_yaml, base_weights=base_weights, epochs=epochs, image_size=imgsz, batch_size=batch)
    typer.echo(json.dumps({"best_weights": str(best_weights_path)}))


def write_annotated_image(output_path: Path, annotated_image: np.ndarray) -> None:
    with log_call(logger, "write_annotated_image", output_path=str(output_path)):
        if not cv2.imwrite(str(output_path), annotated_image):
            raise ImageWriteError(f"Could not write an image to {output_path}")


def format_scan_result_as_json(scan_result: ScanResult) -> str:
    return json.dumps(asdict(scan_result), indent=2)


def main() -> None:
    configure_logging()
    app()
