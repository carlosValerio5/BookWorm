from pathlib import Path

import cv2
import numpy as np
import pillow_heif
import structlog

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

HEIF_FILE_SUFFIXES = frozenset({".heic", ".heif"})


class ImageLoadError(Exception):
    pass


def load_image(image_path: Path) -> np.ndarray:
    with log_call(logger, "load_image", image_path=str(image_path)):
        image = read_heif_image(image_path) if is_heif_file(image_path) else read_opencv_image(image_path)
        logger.info("image_loaded", image_path=str(image_path), image_height=image.shape[0], image_width=image.shape[1])
    return image


def is_heif_file(image_path: Path) -> bool:
    return image_path.suffix.lower() in HEIF_FILE_SUFFIXES


def read_opencv_image(image_path: Path) -> np.ndarray:
    image = cv2.imread(str(image_path))
    if image is None:
        raise ImageLoadError(f"Could not read an image at {image_path}")
    return image


def read_heif_image(image_path: Path) -> np.ndarray:
    try:
        heif_file = pillow_heif.open_heif(image_path, convert_hdr_to_8bit=True, bgr_mode=True)
        bgr_pixels = np.asarray(heif_file)
    except (OSError, ValueError) as error:
        raise ImageLoadError(f"Could not read a HEIF image at {image_path}") from error
    return bgr_pixels
