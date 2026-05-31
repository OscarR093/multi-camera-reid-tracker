import uuid
import time
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from reid.matcher import ReIDMatcher
from storage.redis_client import RedisClient
from storage.sqlite_client import SQLiteClient

logger = logging.getLogger(__name__)


class IdentityManager:
    def __init__(
        self,
        redis_client: RedisClient,
        sqlite_client: SQLiteClient,
        matcher: ReIDMatcher,
        ttl: int = 600,
    ):
        self.redis = redis_client
        self.sqlite = sqlite_client
        self.matcher = matcher
        self.ttl = ttl

    def process_detection(
        self,
        camera_id: str,
        local_track_id: int,
        embedding: np.ndarray,
        height: float,
        centroid: Tuple[float, float],
        timestamp: float,
    ) -> Optional[str]:
        existing_global_id = self.redis.get_local_track_global_id(
            camera_id, local_track_id
        )

        all_candidates = self.redis.get_all_identities()

        if existing_global_id and existing_global_id in {
            c["global_id"] for c in all_candidates
        }:
            best_id, best_score = self._find_best_match(
                embedding, height, all_candidates
            )

            if best_id and best_id != existing_global_id and best_score >= 0.90:
                logger.info(
                    f"[MERGE] {camera_id} T{local_track_id}: {existing_global_id[:8]} "
                    f"-> {best_id[:8]} (score={best_score:.3f})"
                )
                self._merge_identities(existing_global_id, best_id)
                existing_global_id = best_id

            self._update_identity(
                existing_global_id, camera_id, embedding, height, timestamp
            )
            return existing_global_id

        matched_global_id, matched_score = self.matcher.match_with_score(
            embedding, height, all_candidates
        )

        if matched_global_id:
            if existing_global_id and existing_global_id != matched_global_id:
                self._merge_identities(existing_global_id, matched_global_id)

            logger.info(
                f"[MATCH] {camera_id} T{local_track_id} -> {matched_global_id[:8]} "
                f"(score={matched_score:.3f}, candidates={len(all_candidates)})"
            )
            self._update_identity(
                matched_global_id, camera_id, embedding, height, timestamp
            )
            self.redis.link_local_track(
                camera_id, local_track_id, matched_global_id
            )
            return matched_global_id

        if existing_global_id:
            logger.debug(
                f"[ORPHAN] {camera_id} T{local_track_id} keeps {existing_global_id[:8]}"
            )
            self._update_identity(
                existing_global_id, camera_id, embedding, height, timestamp
            )
            return existing_global_id

        global_id = self._create_identity(
            camera_id, local_track_id, embedding, height, timestamp
        )
        logger.info(
            f"[NEW] {camera_id} T{local_track_id} created {global_id[:8]} "
            f"(candidates={len(all_candidates)})"
        )
        return global_id

    def _find_best_match(
        self,
        embedding: np.ndarray,
        height: float,
        candidates: List[Dict],
    ) -> Tuple[Optional[str], float]:
        best_id = None
        best_score = 0.0
        for candidate in candidates:
            cand_emb = np.array(candidate["embedding"], dtype=np.float32)
            cand_height = candidate["height"]
            sim = self.matcher.compute_similarity(
                embedding, height, cand_emb, cand_height
            )
            if sim > best_score:
                best_score = sim
                best_id = candidate["global_id"]
        return best_id, best_score

    def _merge_identities(
        self, source_global_id: str, target_global_id: str
    ):
        source = self.redis.get_identity(source_global_id)
        target = self.redis.get_identity(target_global_id)
        if not source or not target:
            return
        if source["entry_time"] < target["entry_time"]:
            keep_id = source_global_id
            merge_id = target_global_id
        else:
            keep_id = target_global_id
            merge_id = source_global_id

        self.redis.delete_identity(merge_id)
        self.redis.reassign_global_id_links(merge_id, keep_id)

        self.sqlite.log_event(
            global_id=keep_id,
            camera_id="system",
            event_type="merge",
            embedding=None,
            height=None,
            timestamp=time.time(),
        )

        logger.debug(f"Merged identity {merge_id} into {keep_id}")

    def _create_identity(
        self,
        camera_id: str,
        local_track_id: int,
        embedding: np.ndarray,
        height: float,
        timestamp: float,
    ) -> str:
        global_id = str(uuid.uuid4())

        self.redis.set_identity(
            global_id=global_id,
            embedding=embedding,
            height=height,
            camera_id=camera_id,
            timestamp=timestamp,
            ttl=self.ttl,
        )

        self.redis.link_local_track(camera_id, local_track_id, global_id)

        self.sqlite.log_event(
            global_id=global_id,
            camera_id=camera_id,
            event_type="enter",
            embedding=embedding,
            height=height,
            timestamp=timestamp,
        )

        logger.debug(f"New identity created: {global_id} (cam={camera_id})")
        return global_id

    def _update_identity(
        self,
        global_id: str,
        camera_id: str,
        embedding: np.ndarray,
        height: float,
        timestamp: float,
    ):
        existing = self.redis.get_identity(global_id)

        if existing:
            existing_emb = np.array(existing["embedding"], dtype=np.float32)
            alpha = 0.1
            smoothed_emb = (1 - alpha) * existing_emb + alpha * embedding
            norm = np.linalg.norm(smoothed_emb)
            if norm > 0:
                smoothed_emb /= norm

            existing_height = existing["height"]
            smoothed_height = (1 - alpha) * existing_height + alpha * height

            self.redis.update_identity(
                global_id=global_id,
                embedding=smoothed_emb,
                height=smoothed_height,
                camera_id=camera_id,
                timestamp=timestamp,
                ttl=self.ttl,
            )

            self.sqlite.log_event(
                global_id=global_id,
                camera_id=camera_id,
                event_type="heartbeat",
                embedding=smoothed_emb,
                height=smoothed_height,
                timestamp=timestamp,
            )
        else:
            self._create_identity(
                camera_id, 0, embedding, height, timestamp
            )

    def remove_stale_track(
        self, camera_id: str, local_track_id: int
    ):
        global_id = self.redis.get_local_track_global_id(
            camera_id, local_track_id
        )
        if global_id:
            self.redis.unlink_local_track(camera_id, local_track_id)
            self.sqlite.log_event(
                global_id=global_id,
                camera_id=camera_id,
                event_type="exit",
                embedding=None,
                height=None,
                timestamp=time.time(),
            )

    def get_active_count(self) -> int:
        return self.redis.get_active_count()

    def get_active_identities(self) -> List[Dict]:
        return self.redis.get_all_identities()

    def flush_camera(self, camera_id: str):
        self.redis.flush_camera(camera_id)
        logger.info(f"Flushed identities for camera {camera_id}")
