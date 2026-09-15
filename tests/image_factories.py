from pathlib import Path

import cv2
import numpy as np
import zxingcpp

WHITE = 255
BLACK_BGR = (0, 0, 0)
VALID_ISBN13 = "9780306406157"
VALID_NON_ISBN_EAN13 = "4006381333931"


def create_blank_image(height: int = 480, width: int = 640) -> np.ndarray:
    return np.full((height, width, 3), WHITE, dtype=np.uint8)


def create_ean13_image(code: str) -> np.ndarray:
    barcode = zxingcpp.create_barcode(code, zxingcpp.BarcodeFormat.EAN13)
    grayscale_image = np.array(barcode.to_image(scale=4))
    return cv2.cvtColor(grayscale_image, cv2.COLOR_GRAY2BGR)


def create_text_image(text: str) -> np.ndarray:
    image = create_blank_image(height=160, width=1400)
    cv2.putText(image, text, (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 2.0, BLACK_BGR, 4, cv2.LINE_AA)
    return image


def place_on_white_canvas(image: np.ndarray, top: int, left: int, padding: int = 100) -> np.ndarray:
    height, width = image.shape[:2]
    canvas = create_blank_image(height=top + height + padding, width=left + width + padding)
    canvas[top : top + height, left : left + width] = image
    return canvas


def write_image(image_path: Path, image: np.ndarray) -> Path:
    cv2.imwrite(str(image_path), image)
    return image_path
