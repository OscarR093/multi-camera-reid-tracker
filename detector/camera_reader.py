import cv2
import time
from typing import Optional, Tuple
import numpy as np


class CameraReader:
    def __init__(self, source: str, fps: float = 30, loop: bool = False):
        self.source = source
        self.target_fps = fps
        self.loop = loop
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_rtsp = source.startswith("rtsp://")
        self.last_frame_time = 0.0
        self._frame_interval = 1.0 / fps
        self._connected = False
        self._resolution: Tuple[int, int] = (0, 0)
        self._loop_count = 0

    def connect(self) -> bool:
        if self.is_rtsp:
            self.cap = cv2.VideoCapture(
                self.source, cv2.CAP_FFMPEG
            )
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            self.cap = cv2.VideoCapture(self.source)

        self._connected = self.cap.isOpened()
        if self._connected:
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._resolution = (w, h)
        return self._connected

    def _reconnect(self) -> bool:
        self.disconnect()
        self._loop_count += 1
        return self.connect()

    def disconnect(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self._connected = False

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if self.cap is None or not self._connected:
            return False, None

        current_time = time.time()
        elapsed = current_time - self.last_frame_time

        if elapsed < self._frame_interval:
            return False, None

        if self.is_rtsp:
            for _ in range(3):
                ret, _ = self.cap.read()

        ret, frame = self.cap.read()

        if not ret:
            if self.loop and not self.is_rtsp:
                if self._reconnect():
                    ret, frame = self.cap.read()
            if not ret or frame is None:
                return False, None

        self.last_frame_time = current_time
        return True, frame

    @property
    def fps(self) -> float:
        if self.cap is not None:
            return self.cap.get(cv2.CAP_PROP_FPS)
        return 0.0

    @property
    def resolution(self) -> Tuple[int, int]:
        return self._resolution

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def loop_count(self) -> int:
        return self._loop_count
