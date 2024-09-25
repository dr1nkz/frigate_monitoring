import argparse
from collections import defaultdict, deque
from datetime import datetime
import os
import sys
import time as system_time

import cv2
import numpy as np
import supervision as sv

from detector import YOLOv8, Detections
from view_transformer import view_transformer
from request_utils import (
    get_camera_address_from_config,
    get_end_time,
    set_retain_to_true,
    set_sub_label,
    get_transform_points_from_config,
    get_permitted_speed,
    download_event_clip,
    delete_event_clip
)


class SpeedEstimator:
    """
    Class for speed estimation of bojects
    """

    def __init__(self, model_path):
        self.yolov8_detector = YOLOv8(path=model_path,
                                      conf_thres=0.3,
                                      iou_thres=0.5)

    def __call__(self, camera: str, event_id: str):
        self.speed_estimation(camera, event_id)

    def speed_estimation(self, camera: str, event_id: str):
        """
        Speed estimation process

        :camera: str - camera name
        :event_id: str - id of the event        
        :cap: cv2.VideoCapture - VideoCapturing object
        """

        # Get camera address
        # address = f'rtsp://localhost:8554/{camera}'
        # address = get_camera_address(camera, login, password)
        # address = get_camera_address_from_config(camera)

        # Download clip of the event
        if not download_event_clip(event_id):
            return

        # Videocapturing
        # cv2.namedWindow('stream', cv2.WINDOW_NORMAL)
        cap = cv2.VideoCapture(f'/mqtt/speed_estimation/temp/{event_id}.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Videowriting
        start_time = datetime.now()
        directory = '/storage/' + start_time.strftime(r'%d.%m.%Y/')
        if not os.path.isdir(directory):
            os.mkdir(directory)
        filename = directory + camera + \
            start_time.strftime(r'_%H:%M:%S_') + event_id + '.mp4'
        out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        print(filename)

        # Get end time of the event
        end_time = get_end_time(event_id)

        # For affine transforms
        SOURCE, TARGET = get_transform_points_from_config(camera=camera)
        if SOURCE is None and TARGET is None and os.path.isfile(filename):
            system_time.sleep(1)
            os.remove(filename)
            return

        print(f'get_transform_points {SOURCE} {TARGET}')
        coordinates = defaultdict(lambda: deque(maxlen=fps))
        transformer = view_transformer(source=SOURCE, target=TARGET)

        # Byte tracker for id of the object
        byte_track = sv.ByteTrack(frame_rate=fps,
                                  track_thresh=0.3)

        # Maximal detected speed
        max_detected_speed = 0

        # Permitted speed to move
        permitted_speed = get_permitted_speed(camera=camera)
        while cap.isOpened() and end_time is None:
            # Кадр с камеры
            ret, frame = cap.read()
            if not ret:
                break

            # Detecting
            detected_img = frame.copy()
            bounding_boxes, scores, class_ids = self.yolov8_detector(
                detected_img)
            # print(bounding_boxes)
            bounding_boxes = np.array(bounding_boxes)[class_ids == 0]
            scores = np.array(scores)[class_ids == 0]
            class_ids = np.array(class_ids)[class_ids == 0]
            detected_img = self.yolov8_detector.draw_detections(detected_img)
            if detected_img is None:
                continue

            # iou fix if len == 1
            if len(bounding_boxes) == 1 or bounding_boxes.shape[0] == 1:
                # bounding_boxes = np.array([bounding_boxes])
                bounding_boxes = np.array(bounding_boxes).reshape(1, -1)

            # Byte tracker
            detections = Detections(xyxy=bounding_boxes, confidence=scores,
                                    class_id=class_ids, tracker_id=[None] * len(bounding_boxes))
            if len(detections.xyxy) != 0:
                detections = byte_track.update_with_detections(
                    detections=detections)

            # Bottom center anchors
            points = np.array([[x_1 + x_2 / 2, y]
                               for [x_1, _, x_2, y] in detections.xyxy])
            points = transformer.transform_points(points=points).astype(int)

            for tracker_id, point in zip(detections.tracker_id, points):
                coordinates[tracker_id].append(point)

            # for class_id, bounding_box in zip(class_ids, bounding_boxes):
            for tracker_id, bounding_box in zip(detections.tracker_id, bounding_boxes):
                # wait to have enough data
                if len(coordinates[tracker_id]) > fps / 2:
                    # calculate the speed
                    x_start = coordinates[tracker_id][-1][0]
                    x_end = coordinates[tracker_id][0][0]
                    y_start = coordinates[tracker_id][-1][1]
                    y_end = coordinates[tracker_id][0][1]
                    distance = np.sqrt((x_end - x_start)**2 +
                                       (y_end - y_start)**2) / 10

                    time = len(coordinates[tracker_id]) / fps
                    speed = round(distance / time * 3.6, 2)

                    max_detected_speed = speed if speed > max_detected_speed else max_detected_speed

                    if (max_detected_speed > permitted_speed):
                        set_retain_to_true(event_id)
                        set_sub_label(
                            event_id, f'Max speed: {max_detected_speed} km/h')

                    # Caption on the frame
                    caption = f'#{tracker_id} {speed} km/h'  # caption
                    font = cv2.FONT_HERSHEY_SIMPLEX  # font
                    fontScale = 1  # fontScale
                    thickness = 2  # Line thickness of 2 px
                    x_1 = bounding_box[0]
                    y_1 = bounding_box[1]
                    x_2 = bounding_box[2]
                    y_2 = bounding_box[3]
                    # Using cv2.putText() method
                    # cv2.putText(detected_img, caption, (int(x_1 + 2), int(y_1 + (y_2 - y_1) / 2)),
                    #             font, fontScale, (255, 0, 0), thickness, cv2.LINE_AA)

                    x, y = int(x_1) + 70, int(y_1 - 4 * thickness)
                    (text_width, text_height), baseline = cv2.getTextSize(
                        caption, font, fontScale, thickness)
                    background_color = (254, 254, 254)
                    cv2.rectangle(detected_img, (x, y - text_height), (x + text_width, y + int(baseline/2)),
                                  background_color, thickness=cv2.FILLED)
                    cv2.putText(detected_img, caption, (x, y), font,
                                fontScale, (255, 0, 0), thickness, cv2.LINE_AA)

            # cv2.imshow('stream', detected_img)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

            # Writing frame to file
            out.write(detected_img)  # frame

            end_time = datetime.now()
            if (end_time-start_time).total_seconds() > 300:
                break

            # Get end time of the event
            end_time = get_end_time(event_id)

        # cv2.destroyAllWindows()
        cap.release()
        out.release()
        delete_event_clip(event_id)

        # Postprocessing
        if (max_detected_speed < permitted_speed):
            # pass
            if os.path.isfile(filename):
                system_time.sleep(1)
                os.remove(filename)
        # else:
        #     set_retain_to_true(event_id)
        #     set_sub_label(event_id, f'Max speed: {max_detected_speed} km/h')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('camera')
    parser.add_argument('event_id')
    args = parser.parse_args()

    camera = args.camera
    event_id = args.event_id

    speed_estimator = SpeedEstimator(r'speed_estimation/clips_model.onnx')
    speed_estimator(camera, event_id)
