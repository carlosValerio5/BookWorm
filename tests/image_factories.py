from pathlib import Path

import cv2
import numpy as np
import pillow_heif
import zxingcpp
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

pillow_heif.register_heif_opener()

ACCENTED_TEXT_FONT_PATH = font_manager.findfont("DejaVu Sans")

WHITE = 255
BLACK_BGR = (0, 0, 0)
RED_BGR = (0, 0, 255)
VALID_ISBN13 = "9780306406157"
VALID_NON_ISBN_EAN13 = "4006381333931"
LOSSLESS_HEIF_QUALITY = -1


def create_blank_image(height: int = 480, width: int = 640) -> np.ndarray:
    return np.full((height, width, 3), WHITE, dtype=np.uint8)


def create_solid_color_image(color_bgr: tuple[int, int, int], height: int = 480, width: int = 640) -> np.ndarray:
    return np.full((height, width, 3), color_bgr, dtype=np.uint8)


def create_accented_text_image(text: str) -> np.ndarray:
    canvas = Image.new("RGB", (1000, 200), "white")
    ImageDraw.Draw(canvas).text((30, 40), text, fill="black", font=ImageFont.truetype(ACCENTED_TEXT_FONT_PATH, size=100))
    return cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)


def write_heic_image(image_path: Path, image: np.ndarray) -> Path:
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    Image.fromarray(rgb_image).save(image_path, format="HEIF", quality=LOSSLESS_HEIF_QUALITY)
    return image_path


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
