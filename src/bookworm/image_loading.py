from pathlib import Path

import cv2
import numpy as np
import structlog

from bookworm.logging_setup import log_call

logger = structlog.stdlib.get_logger(__name__)


class ImageLoadError(Exception):
    pass


def load_image(image_path: Path) -> np.ndarray:
    with log_call(logger, "load_image", image_path=str(image_path)):
        image = cv2.imread(str(image_path))
        if image is None:
            raise ImageLoadError(f"Could not read an image at {image_path}")
        logger.info("image_loaded", image_path=str(image_path), image_height=image.shape[0], image_width=image.shape[1])
    return image
