import cv2
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class SoftBiometricsMatcher:
    def __init__(
        self,
        hsv_threshold: float = 0.7,
        height_threshold: float = 0.15,
    ):
        self.hsv_threshold = hsv_threshold
        self.height_threshold = height_threshold

    def compare_hsv(
        self, hist_a: np.ndarray, hist_b: np.ndarray
    ) -> float:
        if hist_a is None or hist_b is None:
            return 0.0
        if hist_a.ndim > 1:
            hist_a = hist_a.flatten()
        if hist_b.ndim > 1:
            hist_b = hist_b.flatten()
        return float(
            cv2.compareHist(
                hist_a.astype(np.float32),
                hist_b.astype(np.float32),
                cv2.HISTCMP_CORREL,
            )
        )

    def compare_height(
        self, height_a: float, height_b: float
    ) -> float:
        if height_a == 0 and height_b == 0:
            return 1.0
        if height_a == 0 or height_b == 0:
            return 0.0
        max_h = max(abs(height_a), abs(height_b))
        diff = abs(height_a - height_b)
        if max_h == 0:
            return 1.0
        return 1.0 - (diff / max_h)

    def compute_similarity(
        self,
        hist_a: np.ndarray,
        height_a: float,
        hist_b: np.ndarray,
        height_b: float,
    ) -> float:
        hsv_sim = self.compare_hsv(hist_a, hist_b)
        height_sim = self.compare_height(height_a, height_b)

        similarity = 0.6 * hsv_sim + 0.4 * height_sim

        return similarity

    def match(
        self,
        query_hist: np.ndarray,
        query_height: float,
        candidates: List[Dict],
    ) -> Optional[str]:
        best_id = None
        best_score = 0.0

        for candidate in candidates:
            cand_hist = np.array(candidate["hsv_hist"], dtype=np.float32)
            cand_height = candidate["height"]

            sim = self.compute_similarity(
                query_hist, query_height, cand_hist, cand_height
            )

            if sim > best_score:
                best_score = sim
                best_id = candidate["global_id"]

        if best_score >= self.hsv_threshold:
            return best_id

        return None

    def match_with_score(
        self,
        query_hist: np.ndarray,
        query_height: float,
        candidates: List[Dict],
    ) -> Tuple[Optional[str], float]:
        best_id = None
        best_score = 0.0

        for candidate in candidates:
            cand_hist = np.array(candidate["hsv_hist"], dtype=np.float32)
            cand_height = candidate["height"]

            sim = self.compute_similarity(
                query_hist, query_height, cand_hist, cand_height
            )

            if sim > best_score:
                best_score = sim
                best_id = candidate["global_id"]

        if best_score >= self.hsv_threshold:
            return best_id, best_score

        return None, best_score
