import os
import time
import argparse
from datetime import datetime
from collections import defaultdict, deque
import json

import cv2
import numpy as np
import requests

from detector import YOLOv8
from request_utils import set_retain_to_true, set_sub_label
from view_transformer import view_transformer


SOURCE = np.array([
    [1252, 787],
    [2298, 803],
    [5039, 2159],
    [-550, 2159]
])

TARGET_WIDTH = 25
TARGET_HEIGHT = 250

TARGET = np.array([
    [0, 0],
    [24, 0],
    [24, 249],
    [0, 249],
])

def speed_estimation(camera, event_id, login, password):
    """
    Запуск модели
    """
    model_path = r'./human_forklift_helmet_vest.onnx'
    yolov8_detector = YOLOv8(path=model_path,
                             conf_thres=0.3,
                             iou_thres=0.5)

    # Get camera address from api
    # address = f'rtsp://localhost:8554/{camera}'
    response = requests.get(r'http://localhost:5000/api/config').text
    response = json.loads(response)
    address = response["cameras"][camera]['ffmpeg']['inputs'][0]['path']
    address = address.replace('*', login, 1).replace('*', password, 1)

    # Videocapturing
    # cv2.namedWindow('stream', cv2.WINDOW_NORMAL)
    cap = cv2.VideoCapture(address)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Videowriting
    filename = f'mqtt/speed_estimation/videos/{camera}_{datetime.now().strftime(r'_%d.%m.%Y_%H:%M:%S')}.mp4'
    out = cv2.VideoWriter(filename, fourcc, 30, (width, height))

    response = requests.get(
        f'http://localhost:5000/api/events/{event_id}').text
    response_json = json.loads(response)
    end_time = response_json['end_time']

    coordinates = defaultdict(lambda: deque(maxlen=fps))
    transformer = view_transformer(source=SOURCE, target=TARGET)

    while cap.isOpened() and end_time is None:
        # Кадр с камеры
        ret, frame = cap.read()
        if not ret:
            break

        # Детектирование
        detected_img = frame.copy()
        bounding_boxes, scores, class_ids = yolov8_detector(detected_img)
        print(bounding_boxes)
        bounding_boxes = np.array(bounding_boxes)
        detected_img = yolov8_detector.draw_detections(detected_img)
        if detected_img is None:
            continue

        # чтобы не ломалось iou
        if len(bounding_boxes) == 1 or bounding_boxes.shape[0] == 1:
            # bounding_boxes = np.array([bounding_boxes])
            bounding_boxes = np.array(bounding_boxes).reshape(1, -1)

        # Bottom center anchors
        points = np.array([[x_1 + x_2 / 2, y]
                          for [x_1, _, x_2, y] in bounding_boxes])
        points = transformer.transform_points(points=points).astype(int)

        # for class_id, [_, y] in zip(class_ids, points):
        for class_id, [_, y] in enumerate(points):
            coordinates[class_id].append(y)

        # for class_id, bounding_box in zip(class_ids, bounding_boxes):
        for class_id, bounding_box in enumerate(bounding_boxes):
            # wait to have enough data
            if len(coordinates[class_id]) > fps / 2:
                # calculate the speed
                coordinate_start = coordinates[class_id][-1]
                coordinate_end = coordinates[class_id][0]
                distance = abs(coordinate_start - coordinate_end)
                time = len(coordinates[class_id]) / fps
                speed = distance / time * 3.6

                caption = f'{int(speed)} km/h'  # надпись
                font = cv2.FONT_HERSHEY_SIMPLEX  # font
                fontScale = 1  # fontScale
                thickness = 2  # Line thickness of 2 px
                x_1 = bounding_box[0]
                y_1 = bounding_box[1]
                x_2 = bounding_box[2]
                y_2 = bounding_box[3]
                # Using cv2.putText() method
                cv2.putText(detected_img, caption, (int(x_1 + 2), int(y_1 + (y_2 - y_1) / 2)),
                            font, fontScale, (255, 0, 0), thickness, cv2.LINE_AA)

        # cv2.imshow('stream', detected_img)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break

        out.write(detected_img) # frame
        
        response = requests.get(
            f'http://localhost:5000/api/events/{event_id}').text
        response_json = json.loads(response)
        end_time = response_json['end_time']

    # cv2.destroyAllWindows()
    cap.release()
    out.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('camera')
    parser.add_argument('event_id')
    parser.add_argument('login')
    parser.add_argument('password')
    args = parser.parse_args()

    camera = args.camera
    event_id = args.event_id
    login = args.login
    password = args.password

    speed_estimation(camera, event_id, login, password)
