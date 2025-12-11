import cv2
import numpy as np
import onnxruntime
import torch
from dataclasses import dataclass


from utils import nms, sigmoid, box_cxcywh_to_xyxy
from request_utils import get_labelmap


@dataclass
class Detections:
    xyxy: np.ndarray
    confidence: np.ndarray
    class_id: np.ndarray
    tracker_id: np.ndarray

    def __len__(self):
        return len(self.class_id)

    def __getitem__(self, index):
        return Detections(xyxy=self.xyxy, confidence=self.confidence,
                          class_id=self.class_id, tracker_id=self.tracker_id)


@dataclass
class BboxesStableframesSpeedsScores:
    bounding_boxes: list
    stable_frames: list
    speeds: list
    scores: list

    def __len__(self):
        return len(self.stable_frames)

    def hampel_with_outliers_replacing(self):
        """
        Hampel filter with outliers replacing
        """
        # Hampel filter (outlier -> np.nan)
        vals = np.array(self.speeds).copy()
        difference = np.abs(np.median(vals)-vals)
        median_abs_deviation = np.median(difference)
        threshold = 3 * median_abs_deviation
        outlier_idx = (difference > threshold) & (vals > np.median(vals))
        vals[outlier_idx] = np.nan

        # Nan replacing with average
        nan_indices = np.isnan(vals)
        for i in np.where(nan_indices)[0]:
            # Получаем предыдущие и последующие значения
            prev_value = vals[i - 1] if i - 1 >= 0 else np.nan
            next_value = vals[i + 1] if i + 1 < vals.shape[0] else np.nan

            # Вычисляем среднее, игнорируя NaN
            avg = round(np.nanmean([prev_value, next_value]), 2)
            vals[i] = avg

        self.speeds = vals.tolist()
        return (self.speeds)

    def pop(self):
        """
        Pop left element in dataclass
        """
        if self.__len__() > 0 and self.stable_frames[0] is True:
            bounding_box = self.bounding_boxes[0]
            self.bounding_boxes = self.bounding_boxes[1:]
            stable_frame = self.stable_frames[0]
            self.stable_frames = self.stable_frames[1:]
            speed = self.speeds[0]
            self.speeds = self.speeds[1:]
            score = self.scores[0]
            self.scores = self.scores[1:]
        else:
            if self.__len__() > 0:
                stable_frame = self.stable_frames[0]
                self.stable_frames = self.stable_frames[1:]
            else:
                stable_frame = False
            bounding_box, speed, score = None, None, None

        return bounding_box, stable_frame, speed, score


def draw_external_detection(image, bounding_box, score):
    """
    Нанесение прямоугольников извне
    """
    # classes = get_labelmap()

    classes = {
        0: 'forklift',
        1: 'cabledrum'
    }

    class_names = list(classes.values())
    # class_names = ['person']
    rng = np.random.default_rng(3)
    colors = rng.uniform(0, 255, size=(len(class_names), 3))

    # Прямоугольники
    color = colors[0]

    x_1, y_1, x_2, y_2 = bounding_box.astype(int)

    # Прямоугольник
    cv2.rectangle(image, (x_1, y_1), (x_2, y_2), color, 2)

    caption = f'{int(score * 100)}%'

    # font
    font = cv2.FONT_HERSHEY_SIMPLEX

    # fontScale
    fontScale = 1

    # Line thickness of 2 px
    thickness = 2

    background_color = (254, 254, 254)
    (_, text_height), baseline = cv2.getTextSize(
        caption, font, fontScale, thickness)
    # cv2.rectangle(image, (x_1, y_1-32), (x_2, y_1),
    #               (254, 254, 254), -1)
    x, y = x_1, y_1 - 4 * thickness
    cv2.rectangle(image, (x, y - text_height), (x_2, y + int(baseline/2)),
                  background_color, thickness=cv2.FILLED)

    # Using cv2.putText() method
    cv2.putText(image, caption, (x, y), font,
                fontScale, color, thickness, cv2.LINE_AA)

    return image


def draw_speed_caption(image, bounding_box, tracker_id, speed):
    # Caption on the frame
    caption = f'#{tracker_id} {speed} km/h'  # caption
    font = cv2.FONT_HERSHEY_SIMPLEX  # font
    fontScale = 1  # fontScale
    thickness = 2  # Line thickness of 2 px
    x_1 = bounding_box[0]
    y_1 = bounding_box[1]
    x_2 = bounding_box[2]
    y_2 = bounding_box[3]

    x, y = int(x_1) + 70, int(y_1 - 4 * thickness)
    (text_width, text_height), baseline = cv2.getTextSize(
        caption, font, fontScale, thickness)
    background_color = (254, 254, 254)
    cv2.rectangle(image, (x, y - text_height), (x + text_width, y + int(baseline/2)),
                  background_color, thickness=cv2.FILLED)
    cv2.putText(image, caption, (x, y), font,
                fontScale, (255, 0, 0), thickness, cv2.LINE_AA)

    return image


class RFDETR:
    """
    Модель RFDETR, преобразованная в onnx формат
    """

    MEANS = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    STDS = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __init__(self, path, conf_thres=0.5, iou_thres=0.5, max_boxes=300):
        self.conf_threshold = conf_thres
        self.iou_threshold = iou_thres
        self.max_boxes = max_boxes

        self.initialize_model(path)

    def __call__(self, image):
        return self.detect_objects(image)

    def initialize_model(self, path):
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

        self.session = onnxruntime.InferenceSession(
            path, providers=providers
        )

        self.get_input_details()
        self.get_output_details()

    def get_input_details(self):
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        _, _, self.input_height, self.input_width = inp.shape

    def get_output_details(self):
        self.output_names = [d.name for d in self.session.get_outputs()]

    def detect_objects(self, image):
        self.img_height, self.img_width = image.shape[:2]

        tensor = self.prepare_input(image)
        outputs = self.inference(tensor)

        self.boxes, self.scores, self.class_ids = self.process_output(outputs)

        return self.boxes, self.scores, self.class_ids

    def prepare_input(self, img_bgr):
        img = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.input_width, self.input_height))

        img = img.astype(np.float32) / 255.0
        img = (img - self.MEANS) / self.STDS

        img = img.transpose(2, 0, 1)
        img = img[np.newaxis, ...]
        return img.astype(np.float32)

    def inference(self, tensor):
        outputs = self.session.run(
            self.output_names, {self.input_name: tensor}
        )
        return outputs

    def process_output(self, outputs):
        """
        RFDETR выдаёт:
        outputs[0] = boxes [N, 4]
        outputs[1] = logits [N, num_classes]
        outputs[2] = masks (иногда) — игнорируем здесь
        """

        pred_boxes = outputs[0][0]          # (N,4)
        pred_logits = outputs[1][0]         # (N,C)

        # Активируем вероятности
        probs = sigmoid(pred_logits)

        # максимальная уверенность по классам
        scores = np.max(probs, axis=1)
        class_ids = np.argmax(probs, axis=1)

        # Сортировка — оставляем только top-K запросов
        idx = np.argsort(scores)[::-1][:self.max_boxes]
        scores = scores[idx]
        class_ids = class_ids[idx]
        pred_boxes = pred_boxes[idx]

        # Фильтрация по уверенности
        mask = scores > self.conf_threshold
        scores = scores[mask]
        class_ids = class_ids[mask]
        pred_boxes = pred_boxes[mask]

        if len(scores) == 0:
            return np.array([]), np.array([]), np.array([])

        # Конвертация cxcywh → xyxy
        boxes_xyxy = box_cxcywh_to_xyxy(pred_boxes)

        # масштабируем обратно в исходный размер изображения
        boxes_xyxy[:, [0, 2]] *= self.img_width
        boxes_xyxy[:, [1, 3]] *= self.img_height

        # NMS
        keep = nms(boxes_xyxy, scores, self.iou_threshold)

        return boxes_xyxy[keep], scores[keep], class_ids[keep]

    def draw_detections(self, image):
        classes = get_labelmap()
        class_names = list(classes.values())

        rng = np.random.default_rng(5)
        colors = rng.uniform(0, 255, size=(len(class_names), 3))

        # Filter only #1 class
        if len(self.boxes) != 0:
            self.boxes = np.array(self.boxes)[self.class_ids == 1]
            self.scores = np.array(self.scores)[self.class_ids == 1]
            self.class_ids = np.array(self.class_ids)[self.class_ids == 1]

        for box, score, class_id in zip(self.boxes, self.scores, self.class_ids):
            color = colors[class_id]
            x_1, y_1, x_2, y_2 = box.astype(int)
            # Прямоугольник
            cv2.rectangle(image, (x_1, y_1), (x_2, y_2), color, 2)
            # Отображение лейблов
            label = class_names[class_id]
            # caption = f'{label} {int(score * 100)}%'
            caption = f'{int(score * 100)}%'
            # font
            font = cv2.FONT_HERSHEY_SIMPLEX
            # fontScale
            fontScale = 1
            # Line thickness of 2 px
            thickness = 2

            background_color = (254, 254, 254)
            (_, text_height), baseline = cv2.getTextSize(
                caption, font, fontScale, thickness)
            x, y = x_1, y_1 - 4 * thickness
            cv2.rectangle(image, (x, y - text_height), (x_2, y + int(baseline/2)),
                          background_color, thickness=cv2.FILLED)

            # Using cv2.putText() method
            cv2.putText(image, caption, (x, y), font,
                        fontScale, color, thickness, cv2.LINE_AA)

        return image

    def get_boxes(self):
        return self.boxes
