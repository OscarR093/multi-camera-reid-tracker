import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple


class SoftBiometricsExtractor:
    def __init__(self, hsv_bins: int = 8):
        self.hsv_bins = hsv_bins

    def extract_hsv_histogram(self, person_crop: np.ndarray) -> np.ndarray:
        mask = self._create_foreground_mask(person_crop)
        hsv = cv2.cvtColor(person_crop, cv2.COLOR_BGR2HSV)
        channels = [0, 1, 2]
        hist_size = [self.hsv_bins, self.hsv_bins, self.hsv_bins]
        ranges = [0, 180, 0, 256, 0, 256]

        hist = cv2.calcHist(
            [hsv], channels, mask, hist_size, ranges
        )
        hist = cv2.normalize(hist, hist).flatten()

        hist_1d = np.zeros(self.hsv_bins * 3, dtype=np.float32)
        for c in range(3):
            for b in range(self.hsv_bins):
                block = hist.reshape(self.hsv_bins, self.hsv_bins, self.hsv_bins)
                if c == 0:
                    hist_1d[b + c * self.hsv_bins] = np.sum(block[b, :, :])
                elif c == 1:
                    hist_1d[b + c * self.hsv_bins] = np.sum(block[:, b, :])
                else:
                    hist_1d[b + c * self.hsv_bins] = np.sum(block[:, :, b])

        total = np.sum(hist_1d)
        if total > 0:
            hist_1d /= total

        return hist_1d

    def _create_foreground_mask(self, person_crop: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(person_crop, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.dilate(edges, kernel, iterations=2)
        return mask

    def extract_height(
        self, bbox: List[float], frame_height: int
    ) -> float:
        _, y1, _, y2 = bbox
        return (y2 - y1) / frame_height

    def extract_centroid(self, bbox: List[float]) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def extract(
        self, frame: np.ndarray, bbox: List[float]
    ) -> Optional[Dict]:
        x1, y1, x2, y2 = map(int, bbox)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)

        if x2 <= x1 or y2 <= y1:
            return None

        person_crop = frame[y1:y2, x1:x2]
        if person_crop.size == 0:
            return None

        hsv_hist = self.extract_hsv_histogram(person_crop)
        height = self.extract_height(bbox, frame.shape[0])
        cx, cy = self.extract_centroid(bbox)

        return {
            "hsv_hist": hsv_hist,
            "height": height,
            "centroid": (cx, cy),
        }
