from functools import cache

import easyocr
import numpy as np
import structlog

from bookworm.logging_setup import log_call
from bookworm.scan_types import BoundingBox, RecognizedText

logger = structlog.stdlib.get_logger(__name__)

TEXT_READER_LANGUAGES = ("en",)

type EasyOcrReading = tuple[list[list[float]], str, float]


@cache
def load_text_reader() -> easyocr.Reader:
    with log_call(logger, "load_text_reader", languages=list(TEXT_READER_LANGUAGES)):
        return easyocr.Reader(list(TEXT_READER_LANGUAGES), gpu=True, verbose=False)


def recognize_text(image: np.ndarray, text_reader: easyocr.Reader) -> list[RecognizedText]:
    with log_call(logger, "recognize_text"):
        raw_readings = text_reader.readtext(image)
        texts = convert_easyocr_output(raw_readings)
        logger.info("text_recognized", text_count=len(texts), texts=[text.text for text in texts])
    return texts


def convert_easyocr_output(raw_readings: list[EasyOcrReading]) -> list[RecognizedText]:
    return [
        RecognizedText(text=text, confidence=round(float(confidence), 4), box=BoundingBox.from_points(corners))
        for corners, text, confidence in raw_readings
    ]
