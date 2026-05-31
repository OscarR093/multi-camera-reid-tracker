from ultralytics import YOLO
import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class YOLODetector:
    def __init__(self, confidence: float = 0.5, device: str = "cpu"):
        self.confidence = confidence
        self.device = device
        self.model = YOLO("yolov8n.pt")
        self._warm_up()

    def _warm_up(self):
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self.model(dummy, verbose=False)
        logger.info("YOLOv8n model warmed up")

    def detect_persons(self, frame: np.ndarray) -> List[dict]:
        results = self.model(
            frame,
            conf=self.confidence,
            classes=[0],
            device=self.device,
            verbose=False,
        )
        detections = []

        if results[0].boxes is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()

            for box, conf in zip(boxes, confs):
                detections.append(
                    {
                        "bbox": [float(x) for x in box],
                        "confidence": float(conf),
                        "class_id": 0,
                    }
                )

        return detections

    def detect(self, frame: np.ndarray) -> List[dict]:
        return self.detect_persons(frame)
