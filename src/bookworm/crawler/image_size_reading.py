import cv2
import numpy as np


class ImageDecodeError(Exception):
    pass


def read_image_long_side(image_bytes: bytes) -> int:
    image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ImageDecodeError(f"Could not decode {len(image_bytes)} bytes as an image")
    return max(image.shape[:2])
