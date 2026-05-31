import numpy as np
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ReIDMatcher:
    def __init__(self, cosine_threshold: float = 0.6, height_threshold: float = 0.15):
        self.cosine_threshold = cosine_threshold
        self.height_threshold = height_threshold

    def cosine_similarity(self, emb_a: np.ndarray, emb_b: np.ndarray) -> float:
        if emb_a is None or emb_b is None:
            return 0.0
        return float(np.dot(emb_a, emb_b))

    def compare_height(self, height_a: float, height_b: float) -> float:
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
        emb_a: np.ndarray,
        height_a: float,
        emb_b: np.ndarray,
        height_b: float,
    ) -> float:
        cos_sim = self.cosine_similarity(emb_a, emb_b)
        height_sim = self.compare_height(height_a, height_b)
        return 0.7 * cos_sim + 0.3 * height_sim

    def match(
        self,
        query_emb: np.ndarray,
        query_height: float,
        candidates: List[Dict],
    ) -> Optional[str]:
        best_id = None
        best_score = 0.0

        for candidate in candidates:
            cand_emb = np.array(candidate["embedding"], dtype=np.float32)
            cand_height = candidate["height"]

            sim = self.compute_similarity(
                query_emb, query_height, cand_emb, cand_height
            )

            if sim > best_score:
                best_score = sim
                best_id = candidate["global_id"]

        if best_score >= self.cosine_threshold:
            return best_id
        return None

    def match_with_score(
        self,
        query_emb: np.ndarray,
        query_height: float,
        candidates: List[Dict],
    ) -> Tuple[Optional[str], float]:
        best_id = None
        best_score = 0.0

        for candidate in candidates:
            cand_emb = np.array(candidate["embedding"], dtype=np.float32)
            cand_height = candidate["height"]

            sim = self.compute_similarity(
                query_emb, query_height, cand_emb, cand_height
            )

            if sim > best_score:
                best_score = sim
                best_id = candidate["global_id"]

        if best_score >= self.cosine_threshold:
            return best_id, best_score
        return None, best_score
