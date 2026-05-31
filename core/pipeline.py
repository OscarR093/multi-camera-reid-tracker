import time
import threading
import logging
from typing import Dict, List, Optional, Set
import numpy as np

from detector.camera_reader import CameraReader
from detector.tracker import PersonTracker
from detector.soft_biometrics import SoftBiometricsExtractor
from reid.embedder import ReIDEmbedder
from reid.matcher import ReIDMatcher
from identity.manager import IdentityManager
from storage.redis_client import RedisClient
from storage.sqlite_client import SQLiteClient
from core.config import settings

logger = logging.getLogger(__name__)

_pipeline_instance: Optional["Pipeline"] = None


def set_pipeline(pipeline: "Pipeline"):
    global _pipeline_instance
    _pipeline_instance = pipeline


def get_pipeline() -> Optional["Pipeline"]:
    return _pipeline_instance


class Pipeline:
    def __init__(self):
        self.camera_sources = settings.camera_list
        self.running = False
        self.readers: Dict[str, CameraReader] = {}
        self.trackers: Dict[str, PersonTracker] = {}
        self.extractors: Dict[str, SoftBiometricsExtractor] = {}
        self.reid_embedder: Optional[ReIDEmbedder] = None
        self.identity_manager: Optional[IdentityManager] = None
        self.callback: Optional[callable] = None

        self._active_local_tracks: Dict[str, Set[int]] = {}
        self._latest_frames: Dict[str, tuple] = {}
        self._frame_lock = threading.Lock()
        self._loop_counts: Dict[str, int] = {}

    def setup(self):
        redis_client = RedisClient(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
        )

        sqlite_client = SQLiteClient(db_path=settings.sqlite_db_path)

        matcher = ReIDMatcher(
            cosine_threshold=settings.hsv_match_threshold,
            height_threshold=settings.height_match_threshold,
        )

        self.identity_manager = IdentityManager(
            redis_client=redis_client,
            sqlite_client=sqlite_client,
            matcher=matcher,
            ttl=settings.identity_ttl,
        )

        self.reid_embedder = ReIDEmbedder()

        for i, source in enumerate(self.camera_sources):
            cam_id = f"cam_{i}"
            reader = CameraReader(source, loop=not source.startswith("rtsp://"))
            if reader.connect():
                self.readers[cam_id] = reader
                self.trackers[cam_id] = PersonTracker(
                    confidence=settings.detection_confidence
                )
                self.extractors[cam_id] = SoftBiometricsExtractor()
                self._active_local_tracks[cam_id] = set()
                self._loop_counts[cam_id] = reader.loop_count
                logger.info(
                    f"Camera {cam_id} connected: {source} "
                    f"({reader.resolution[0]}x{reader.resolution[1]}@{reader.fps:.1f}fps)"
                )
            else:
                logger.error(f"Failed to connect to camera {cam_id}: {source}")

    def set_callback(self, callback: callable):
        self.callback = callback

    def start(self):
        self.setup()
        if not self.readers:
            logger.error("No cameras connected. Aborting.")
            return

        self.running = True

        threads = []
        for cam_id in self.readers:
            t = threading.Thread(
                target=self._camera_loop,
                args=(cam_id,),
                daemon=True,
            )
            threads.append(t)
            t.start()

        try:
            last_hour = ""
            while self.running:
                time.sleep(5)
                current_hour = time.strftime("%Y-%m-%d %H:00")
                if current_hour != last_hour and self.identity_manager:
                    for cam_id in self.readers:
                        count = self.identity_manager.get_active_count()
                        self.identity_manager.sqlite.save_hourly_count(
                            cam_id, current_hour, count
                        )
                    last_hour = current_hour
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def get_latest_frame(self, cam_id: str) -> Optional[tuple]:
        with self._frame_lock:
            return self._latest_frames.get(cam_id)

    def stop(self):
        self.running = False
        for cam_id, reader in self.readers.items():
            reader.disconnect()
            logger.info(f"Camera {cam_id} disconnected")

    def _camera_loop(self, cam_id: str):
        reader = self.readers[cam_id]
        detector = self.trackers[cam_id]
        extractor = self.extractors[cam_id]

        logger.info(f"Camera loop started for {cam_id}")

        while self.running:
            current_loop = reader.loop_count
            if current_loop != self._loop_counts.get(cam_id):
                logger.info(
                    f"[LOOP] {cam_id} video loop detected (count={current_loop}), flushing identities"
                )
                self.identity_manager.flush_camera(cam_id)
                self._active_local_tracks[cam_id] = set()
                self._loop_counts[cam_id] = current_loop

            ret, frame = reader.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            tracks = detector.track(frame)

            current_track_ids = set()
            track_data = []

            person_crops = []
            crop_info = []

            for track in tracks:
                track_id = track["track_id"]
                bbox = track["bbox"]
                current_track_ids.add(track_id)

                x1, y1, x2, y2 = map(int, bbox)
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)

                if x2 > x1 and y2 > y1:
                    crop = frame[y1:y2, x1:x2]
                    if crop.size > 0:
                        person_crops.append(crop)
                        crop_info.append(
                            {"track_id": track_id, "bbox": bbox, "confidence": track["confidence"]}
                        )

            embeddings = []
            if person_crops:
                embeddings = self.reid_embedder.extract_batch(person_crops)

            for i, info in enumerate(crop_info):
                track_id = info["track_id"]
                bbox = info["bbox"]
                emb = embeddings[i] if i < len(embeddings) else None

                if emb is None:
                    continue

                height = extractor.extract_height(bbox, frame.shape[0])
                cx, cy = extractor.extract_centroid(bbox)

                global_id = self.identity_manager.process_detection(
                    camera_id=cam_id,
                    local_track_id=track_id,
                    embedding=emb,
                    height=height,
                    centroid=(cx, cy),
                    timestamp=time.time(),
                )

                track_data.append(
                    {
                        "local_track_id": track_id,
                        "global_id": global_id,
                        "bbox": bbox,
                        "confidence": info["confidence"],
                    }
                )

            stale_tracks = self._active_local_tracks[cam_id] - current_track_ids
            for stale_track_id in stale_tracks:
                self.identity_manager.remove_stale_track(cam_id, stale_track_id)

            self._active_local_tracks[cam_id] = current_track_ids

            with self._frame_lock:
                self._latest_frames[cam_id] = (frame.copy(), track_data)

            if self.callback:
                self.callback(cam_id, track_data, len(track_data))

            time.sleep(0.01)
