import numpy as np
import onnxruntime as ort
import cv2
import logging
import os
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


class ReIDEmbedder:
    def __init__(self, model_path: Optional[str] = None, device: str = "cpu"):
        if model_path is None:
            model_path = os.path.join(_MODEL_DIR, "reid_mobilenet_v3.onnx")

        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if device == "cuda"
            else ["CPUExecutionProvider"]
        )

        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 2
        sess_options.inter_op_num_threads = 2

        self.session = ort.InferenceSession(
            model_path, sess_options, providers=providers
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        self.input_size = (256, 128)

        logger.info(
            f"ReID embedder loaded: {os.path.basename(model_path)} "
            f"(input={self.input_size}, providers={providers[0]})"
        )

    def preprocess(self, crop: np.ndarray) -> np.ndarray:
        img = cv2.resize(crop, (self.input_size[1], self.input_size[0]))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img = (img - mean) / std
        img = np.transpose(img, (2, 0, 1))
        return img

    def extract_embedding(self, person_crop: np.ndarray) -> Optional[np.ndarray]:
        if person_crop is None or person_crop.size == 0:
            return None
        try:
            tensor = self.preprocess(person_crop)
            tensor = np.expand_dims(tensor, axis=0)
            result = self.session.run([self.output_name], {self.input_name: tensor})
            embedding = result[0][0].astype(np.float32)
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding /= norm
            return embedding
        except Exception as e:
            logger.warning(f"ReID extraction failed: {e}")
            return None

    def extract_batch(self, crops: List[np.ndarray]) -> List[Optional[np.ndarray]]:
        if not crops:
            return []
        tensors = []
        valid_indices = []
        for i, crop in enumerate(crops):
            if crop is not None and crop.size > 0:
                tensors.append(self.preprocess(crop))
                valid_indices.append(i)
        if not tensors:
            return [None] * len(crops)

        batch = np.stack(tensors, axis=0)
        result = self.session.run([self.output_name], {self.input_name: batch})
        embeddings = result[0].astype(np.float32)

        for e in embeddings:
            norm = np.linalg.norm(e)
            if norm > 0:
                e /= norm

        output = [None] * len(crops)
        for i, idx in enumerate(valid_indices):
            output[idx] = embeddings[i]
        return output
