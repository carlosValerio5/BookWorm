import asyncio
import base64
import binascii
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import structlog
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from bookworm.book_detection import detect_books, load_book_detector
from bookworm.image_loading import shrink_image_to_long_side
from bookworm.logging_setup import calculate_elapsed_ms, log_call
from bookworm.scan_classification import scale_boxes_to_original, scan_image
from bookworm.scan_types import BookDetection, ScanResult
from bookworm.text_recognition import load_text_reader

logger = structlog.stdlib.get_logger(__name__)

LIVE_DETECT_MAX_LONG_SIDE = 640


class ScanRequest(BaseModel):
    image: str


class ScanPhotoDecodeError(Exception):
    pass


class FrameDecodeError(Exception):
    pass


class LatestFrameBuffer:
    def __init__(self) -> None:
        self._frame_bytes: bytes = b""
        self._frame_ready = asyncio.Event()
        self.disconnected = False

    def set(self, frame_bytes: bytes) -> None:
        self._frame_bytes = frame_bytes
        self._frame_ready.set()

    def mark_disconnected(self) -> None:
        self.disconnected = True
        self._frame_ready.set()

    async def wait_for_next(self) -> bytes:
        await self._frame_ready.wait()
        self._frame_ready.clear()
        return self._frame_bytes


def create_mobile_app(photos_dir: Path) -> FastAPI:
    app = FastAPI(title="BookWorm Mobile API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    photos_dir.mkdir(parents=True, exist_ok=True)

    @app.post("/api/scan")
    def scan_book(payload: ScanRequest) -> ScanResult:
        with log_call(logger, "scan_book"):
            try:
                photo_path = save_scan_photo(photos_dir, payload.image)
            except ScanPhotoDecodeError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
            return scan_image(photo_path, load_book_detector(), load_text_reader())

    @app.websocket("/api/live-detect")
    async def live_detect(websocket: WebSocket) -> None:
        await run_live_detect_session(websocket)

    return app


def save_scan_photo(photos_dir: Path, data_url: str) -> Path:
    with log_call(logger, "save_scan_photo"):
        try:
            _header, encoded = data_url.split(",", 1)
            image_bytes = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ScanPhotoDecodeError("Could not decode the submitted photo") from error
        photo_path = photos_dir / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        photo_path.write_bytes(image_bytes)
    return photo_path


def detect_frame_boxes(frame_bytes: bytes) -> list[BookDetection]:
    with log_call(logger, "detect_frame_boxes"):
        frame = cv2.imdecode(np.frombuffer(frame_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise FrameDecodeError("Could not decode a JPEG frame for live detection")
        shrunk_frame = shrink_image_to_long_side(frame, LIVE_DETECT_MAX_LONG_SIDE)
        boxes = detect_books(shrunk_frame.pixels, load_book_detector())
    return scale_boxes_to_original(boxes, shrunk_frame.scale_to_original)


async def receive_frames_into_buffer(websocket: WebSocket, buffer: LatestFrameBuffer) -> None:
    try:
        while True:
            buffer.set(await websocket.receive_bytes())
    except WebSocketDisconnect:
        buffer.mark_disconnected()


async def run_live_detect_session(websocket: WebSocket) -> None:
    await websocket.accept()
    latest_frame = LatestFrameBuffer()
    receiver_task = asyncio.create_task(receive_frames_into_buffer(websocket, latest_frame))
    frame_count = 0
    total_latency_ms = 0.0
    session_started_at = time.perf_counter()
    try:
        while not latest_frame.disconnected:
            frame_bytes = await latest_frame.wait_for_next()
            if latest_frame.disconnected:
                break
            frame_started_at = time.perf_counter()
            try:
                boxes = detect_frame_boxes(frame_bytes)
            except FrameDecodeError:
                continue
            await websocket.send_json({"boxes": [asdict(box) for box in boxes]})
            frame_count += 1
            total_latency_ms += calculate_elapsed_ms(frame_started_at)
    finally:
        receiver_task.cancel()
        logger.info(
            "live_detect_session_finished",
            frame_count=frame_count,
            session_duration_ms=calculate_elapsed_ms(session_started_at),
            average_frame_latency_ms=round(total_latency_ms / frame_count, 2) if frame_count else 0.0,
        )
