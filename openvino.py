import logging
import numpy as np

from pydantic import Field
from typing_extensions import Literal

from frigate.detectors.detection_api import DetectionApi
from frigate.detectors.detector_config import BaseDetectorConfig

from frigate.detectors.detector_rfdetr import RFDETR

logger = logging.getLogger(__name__)

DETECTOR_KEY = "openvino"


class OvDetectorConfig(BaseDetectorConfig):
    type: Literal[DETECTOR_KEY]
    device: str = Field(default=None, title="Device Type")


class OvDetector(DetectionApi):
    type_key = DETECTOR_KEY

    def __init__(self, detector_config: OvDetectorConfig):
        self.h = detector_config.model.height
        self.w = detector_config.model.width

        # инициализация RFDETR
        self.model = RFDETR(
            path=detector_config.model.path,
            conf_thres=0.5,
            iou_thres=0.5,
            max_boxes=20,
        )

        logger.info(
            "RFDETR ONNX detector initialized (openvino backend overridden)"
        )

    def detect_raw(self, tensor_input: np.ndarray) -> np.ndarray:
        """
        tensor_input:
            np.ndarray (H, W, 3), BGR uint8

        return:
            np.ndarray (20, 6) float32
            [class_id, confidence, y_min, x_min, y_max, x_max]
            координаты нормализованы (0..1)
        """

        boxes, scores, class_ids = self.model(tensor_input)

        detections = np.zeros((20, 6), dtype=np.float32)

        if len(scores) == 0:
            return detections

        img_h, img_w = tensor_input.shape[:2]

        for i, (box, score, cls) in enumerate(
            zip(boxes, scores, class_ids)
        ):
            if i >= 20:
                break

            x1, y1, x2, y2 = box

            detections[i] = [
                float(cls),
                float(score),
                y1 / img_h,
                x1 / img_w,
                y2 / img_h,
                x2 / img_w,
            ]

        return detections
