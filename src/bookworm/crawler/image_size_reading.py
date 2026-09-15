import io

import imagesize


class ImageDecodeError(Exception):
    pass


def read_image_long_side(image_bytes: bytes) -> int:
    width, height = imagesize.get(io.BytesIO(image_bytes))
    if min(width, height) <= 0:
        raise ImageDecodeError(f"Could not read image dimensions from {len(image_bytes)} bytes")
    return max(width, height)
