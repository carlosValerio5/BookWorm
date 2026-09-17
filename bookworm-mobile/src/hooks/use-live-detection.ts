import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { manipulateAsync, SaveFormat } from 'expo-image-manipulator';

import { liveDetectWebSocketUrl } from '../services/api';
import { DetectionBox, Size, shouldCaptureFrame } from './live-detection-geometry';

const CAPTURE_INTERVAL_MS = 500;
const LIVE_FRAME_WIDTH = 480;
const LIVE_FRAME_COMPRESSION = 0.5;

export function useLiveDetection(cameraRef: RefObject<any>, isActive: boolean) {
  const [box, setBox] = useState<DetectionBox | null>(null);
  const [frameSize, setFrameSize] = useState<Size | null>(null);
  const lastCaptureAtRef = useRef(0);
  const capturingRef = useRef(false);

  useEffect(() => {
    if (!isActive) {
      setBox(null);
      setFrameSize(null);
      return;
    }

    const socket = new WebSocket(liveDetectWebSocketUrl());

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        setBox(payload.boxes?.[0] ?? null);
      } catch (error) {
        console.error('Error al leer detección en vivo:', error);
      }
    };
    socket.onerror = () => setBox(null);
    socket.onclose = () => setBox(null);

    const intervalId = setInterval(async () => {
      const now = Date.now();
      if (
        capturingRef.current ||
        !shouldCaptureFrame(lastCaptureAtRef.current, now, CAPTURE_INTERVAL_MS) ||
        socket.readyState !== WebSocket.OPEN ||
        !cameraRef.current
      ) {
        return;
      }

      capturingRef.current = true;
      lastCaptureAtRef.current = now;
      try {
        const photo = await cameraRef.current.takePictureAsync({ quality: 0.3, skipProcessing: true });
        const resized = await manipulateAsync(photo.uri, [{ resize: { width: LIVE_FRAME_WIDTH } }], {
          base64: true,
          compress: LIVE_FRAME_COMPRESSION,
          format: SaveFormat.JPEG,
        });
        if (!resized.base64) {
          return;
        }
        setFrameSize({ width: resized.width, height: resized.height });
        socket.send(resized.base64);
      } catch (error) {
        console.error('Error al capturar cuadro en vivo:', error);
      } finally {
        capturingRef.current = false;
      }
    }, CAPTURE_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
      socket.close();
    };
  }, [isActive, cameraRef]);

  return { box, frameSize };
}
