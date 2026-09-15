from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pillow_heif
import structlog

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)

HEIF_FILE_SUFFIXES = frozenset({".heic", ".heif"})
MAX_SCAN_LONG_SIDE = 1280


class ImageLoadError(Exception):
    pass


@dataclass(frozen=True, eq=False)
class ShrunkImage:
    pixels: np.ndarray
    scale_to_original: float


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


def shrink_image_to_long_side(image: np.ndarray, max_long_side: int) -> ShrunkImage:
    with log_call(logger, "shrink_image_to_long_side", max_long_side=max_long_side):
        shrink_factor = min(1.0, max_long_side / max(image.shape[:2]))
        shrunk_pixels = cv2.resize(image, None, fx=shrink_factor, fy=shrink_factor, interpolation=cv2.INTER_AREA)
        logger.info(
            "image_shrunk",
            original_height=image.shape[0],
            original_width=image.shape[1],
            shrunk_height=shrunk_pixels.shape[0],
            shrunk_width=shrunk_pixels.shape[1],
        )
    return ShrunkImage(pixels=shrunk_pixels, scale_to_original=1 / shrink_factor)
