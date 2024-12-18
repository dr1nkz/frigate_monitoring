import time
import cv2
import numpy as np
import torch
import onnxruntime
from dataclasses import dataclass


from utils import xywh2xyxy, nms, compute_iou
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


class YOLOv8:
    """
    Модель YOLO, преобразованная в onnx формат
    """

    def __init__(self, path, conf_thres=0.7, iou_thres=0.5):
        self.conf_threshold = conf_thres
        self.iou_threshold = iou_thres

        # Инициализация модели
        self.initialize_model(path)

    def __call__(self, image):
        return self.detect_objects(image)

    def initialize_model(self, path):
        """
        Инициализация модели

        :param path: путь к модели
        """
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        # providers = ['CPUExecutionProvider']
        # Основной класс для запуска модели
        self.session = onnxruntime.InferenceSession(path,
                                                    providers=providers)

        # Получение информации о модели
        self.get_input_details()
        self.get_output_details()

    def detect_objects(self, image):
        """
        Детекция изображения

        :param image: np.array - прочитанное изображение в массив
        """
        input_tensor = self.prepare_input(image)

        # Результат предикции
        outputs = self.inference(input_tensor)

        self.boxes, self.scores, self.class_ids = self.process_output(outputs)

        return self.boxes, self.scores, self.class_ids

    def prepare_input(self, image):
        """
        Подготавливает изображение

        :param image: np.array - прочитанное изображение в массив
        """
        self.img_height, self.img_width = image.shape[:2]

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Ресайз изображения
        image = cv2.resize(image, (640, 640), interpolation=cv2.INTER_LINEAR)

        # Скалирование изображения
        image = image / 255.0
        image = image.transpose(2, 0, 1)
        input_tensor = image[np.newaxis, :, :, :].astype(np.float32)

        return input_tensor

    def inference(self, input_tensor):
        """
        Инференс модели

        :param input_tensor: np.array - подготовленное изображение
        """
        start = time.perf_counter()
        outputs = self.session.run(
            self.output_names, {self.input_names[0]: input_tensor})

        # print(f"Inference time: {(time.perf_counter() - start)*1000:.2f} ms")
        return outputs

    def process_output(self, output):
        """
        Подготовка результатов модели
        """
        predictions = np.squeeze(output[0]).T

        # Фильтрафия оценок, которые ниже уверенности модели
        scores = np.max(predictions[:, 4:], axis=1)
        predictions = predictions[scores > self.conf_threshold, :]
        scores = scores[scores > self.conf_threshold]

        if len(scores) == 0:
            return [], [], []

        # Класс с наибольшей уверенностью
        class_ids = np.argmax(predictions[:, 4:], axis=1)

        # Прямоугольники для каждого предсказания
        self.extract_boxes(predictions)

        # Применение метода nms
        indices = nms(self.boxes, scores, self.iou_threshold)

        return self.boxes[indices], scores[indices], class_ids[indices]

    def extract_boxes(self, predictions):
        """
        Извлечение прямоугольников
        """
        # Прямоугольники
        self.boxes = predictions[:, :4]
        # Рескалинг под разрешение изображения
        self.boxes = self.rescale_boxes(self.boxes)
        # Перевод в формат vol
        self.boxes = xywh2xyxy(self.boxes)

    def get_boxes(self):
        """
        Получить прямоугольники из экземпляра класса
        """
        return self.boxes

    def rescale_boxes(self, boxes):
        """
        Рескейл к исходному разрешению
        """
        input_shape = np.array([self.input_width, self.input_height,
                                self.input_width, self.input_height])
        boxes = np.divide(boxes, input_shape, dtype=np.float32)
        boxes *= np.array([self.img_width, self.img_height,
                          self.img_width, self.img_height])
        return boxes

    def draw_detections(self, image):
        """
        Нанесение прямоугольников
        """
        classes = get_labelmap()

        # classes = {
        #     0: 'forklift',
        #     1: 'cabledrum'
        # }

        class_names = list(classes.values())
        # class_names = ['person']
        rng = np.random.default_rng(3)
        colors = rng.uniform(0, 255, size=(len(class_names), 3))

        # Filter only #0 class
        if len(self.boxes) != 0:
            self.boxes = np.array(self.boxes)[self.class_ids == 0]
            self.scores = np.array(self.scores)[self.class_ids == 0]
            self.class_ids = np.array(self.class_ids)[self.class_ids == 0]

        # Прямоугольники
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
            # cv2.rectangle(image, (x_1, y_1-32), (x_2, y_1),
            #               (254, 254, 254), -1)
            x, y = x_1, y_1 - 4 * thickness
            cv2.rectangle(image, (x, y - text_height), (x_2, y + int(baseline/2)),
                          background_color, thickness=cv2.FILLED)

            # Using cv2.putText() method
            cv2.putText(image, caption, (x, y), font,
                        fontScale, color, thickness, cv2.LINE_AA)

        return image

    def get_input_details(self):
        """
        Получение информации из входных данных
        """
        model_inputs = self.session.get_inputs()
        self.input_names = [
            model_inputs[i].name for i in range(len(model_inputs))]

        self.input_shape = model_inputs[0].shape
        self.input_height = self.input_shape[2]
        self.input_width = self.input_shape[3]

    def get_output_details(self):
        """
        Информация о выходных значениях
        """
        model_outputs = self.session.get_outputs()
        self.output_names = [
            model_outputs[i].name for i in range(len(model_outputs))]
