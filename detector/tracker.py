import numpy as np
from ultralytics import YOLO
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class PersonTracker:
    def __init__(self, confidence: float = 0.5, device: str = "cuda"):
        self.confidence = confidence
        self.device = device
        self.model = YOLO("yolov8n.pt")
        self._warm_up()

    def _warm_up(self):
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model.track(dummy, persist=True, verbose=False)
        logger.info("YOLOv8n tracker warmed up")

    def track(self, frame: np.ndarray) -> List[dict]:
        results = self.model.track(
            frame,
            conf=self.confidence,
            classes=[0],
            device=self.device,
            persist=True,
            verbose=False,
            tracker="bytetrack.yaml",
        )

        tracks = []

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()

            for box, track_id, conf in zip(boxes, track_ids, confs):
                tracks.append(
                    {
                        "bbox": [float(x) for x in box],
                        "track_id": int(track_id),
                        "confidence": float(conf),
                    }
                )

        return tracks
