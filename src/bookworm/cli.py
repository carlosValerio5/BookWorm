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
from bookworm.scan_classification import scan_image
from bookworm.scan_types import ScanResult
from bookworm.text_recognition import load_text_reader

logger = structlog.stdlib.get_logger(__name__)

app = typer.Typer(no_args_is_help=True, help="Scan a book photo and tell if it shows a cover or an ISBN.")

ExistingImagePath = Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)]
ExistingDirectoryPath = Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True)]

ANNOTATOR_HOST = "127.0.0.1"
DEFAULT_ANNOTATOR_PORT = 8765
DEFAULT_LABELS_DIRECTORY = Path("labels")
DEFAULT_DRIVE_OUTPUT_DIR = Path("dataset/drive")


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


def write_annotated_image(output_path: Path, annotated_image: np.ndarray) -> None:
    with log_call(logger, "write_annotated_image", output_path=str(output_path)):
        if not cv2.imwrite(str(output_path), annotated_image):
            raise ImageWriteError(f"Could not write an image to {output_path}")


def format_scan_result_as_json(scan_result: ScanResult) -> str:
    return json.dumps(asdict(scan_result), indent=2)


def main() -> None:
    configure_logging()
    app()
