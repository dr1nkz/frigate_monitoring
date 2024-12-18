import argparse
from collections import defaultdict, deque
from datetime import datetime
import os
import sys
import time as system_time
from copy import deepcopy

import cv2
import numpy as np
import supervision as sv

from detector import (
    YOLOv8,
    Detections,
    BboxesStableframesSpeedsScores,
    draw_external_detection,
    draw_speed_caption
)
from view_transformer import view_transformer
from utils import deques_equal, check_consecutive_exceeds
from request_utils import (
    get_camera_address_from_config,
    get_end_time,
    set_retain_to_true,
    set_sub_label,
    get_transform_points_from_api,
    get_all_zones_coordinates_from_api,
    get_permitted_speed,
    download_event_clip,
    delete_event_clip,
    codec_change
)


VIOLATION_DURATION = int(os.getenv('VIOLATION_DURATION', 3))


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

        # Download clip of the event
        if not download_event_clip(event_id):
            return

        # Videocapturing
        cap = cv2.VideoCapture(f'/mqtt/speed_estimation/temp/{event_id}.mp4')
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        start_time = datetime.now()

        # For affine transforms
        SOURCE, TARGET = get_transform_points_from_api(camera=camera)
        if SOURCE is None and TARGET is None:
            return

        print(f'get_transform_points {SOURCE} {TARGET}')
        coordinates = defaultdict(lambda: deque(maxlen=fps))
        transformer = view_transformer(source=SOURCE, target=TARGET)

        # Byte tracker for id of the object
        byte_track = sv.ByteTrack(frame_rate=fps,
                                  track_activation_threshold=0.3)

        # Maximal detected speed
        max_detected_speed = 0

        # Previous coordinates
        coordinates_previous = None

        # Permitted speed to move
        permitted_speed = get_permitted_speed(camera=camera)

        # Allowed zones for bboxes
        allowed_zones = get_all_zones_coordinates_from_api(camera)

        # Unstable frames counter
        unstable_frames_counter = 1

        # Dictionary of BboxStableframesSpeeds
        bsss_dictionary = defaultdict(lambda: BboxesStableframesSpeedsScores)

        print(f'cap.isOpened(): {cap.isOpened()}')
        while cap.isOpened():
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

            # Delete bboxes outside area
            if len(bounding_boxes) != 0 and allowed_zones is not None:
                # Calculate the center points of the bounding boxes
                points = np.array([[(x_1 + x_2) / 2, y]
                                   for [x_1, _, x_2, y] in bounding_boxes]).astype('int')

                # Initialize an array to store whether points are within allowed zones
                point_in_zone = np.zeros(len(points), dtype=bool)

                # Check each allowed zone
                for allowed_zone in allowed_zones:
                    # Update the boolean mask for points within the current allowed zone
                    point_in_zone |= np.array(list(
                        map(lambda x: cv2.pointPolygonTest(allowed_zone, x.tolist(), False) >= 0, points)))

                # Use this mask to filter or index your points or bounding boxes
                bounding_boxes = np.array(
                    [box for index, box in enumerate(bounding_boxes) if point_in_zone[index]])
                scores = np.array(
                    [score for index, score in enumerate(scores) if point_in_zone[index]])
                class_ids = np.array(
                    [class_id for index, class_id in enumerate(class_ids) if point_in_zone[index]])

            # iou fix if len == 1
            if len(bounding_boxes) == 1 or bounding_boxes.shape[0] == 1:
                # bounding_boxes = np.array([bounding_boxes])
                bounding_boxes = np.array(bounding_boxes).reshape(1, -1)

            # Byte tracker
            detections = Detections(xyxy=bounding_boxes, confidence=scores,
                                    class_id=class_ids, tracker_id=[None] * len(bounding_boxes))
            if len(detections.xyxy) != 0:
                try:
                    detections = byte_track.update_with_detections(
                        detections=detections)
                except:
                    print(detections)
            else:
                for key in coordinates:
                    coordinates[key].clear()

            # Bottom center anchors
            points = np.array([[(x_1 + x_2) / 2, y]
                               for [x_1, _, x_2, y] in detections.xyxy])
            points = transformer.transform_points(points=points).astype(int)

            for tracker_id, point in zip(detections.tracker_id, points):
                coordinates[tracker_id].append(point)

            # Check if coordinates are the same (object not tracked)
            if coordinates_previous is not None:
                for key in coordinates:
                    if deques_equal(coordinates[key], coordinates_previous[key]):
                        coordinates[key].clear()
            coordinates_previous = deepcopy(coordinates)

            for id in bsss_dictionary:
                if bsss_dictionary.get(tracker_id) is not None:
                    bsss_dictionary[tracker_id].stable_frames.append(False)

            # Main loop
            for tracker_id, bounding_box, score in zip(detections.tracker_id, bounding_boxes, scores):
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

                    # bsss dictionary data append
                    if bsss_dictionary.get(tracker_id) is None:
                        bsss_dictionary[tracker_id] = BboxesStableframesSpeedsScores(
                            [], [], [], [])
                        bsss_dictionary[tracker_id].stable_frames.extend(
                            unstable_frames_counter*[False])

                    bsss_dictionary[tracker_id].bounding_boxes.append(
                        bounding_box)
                    bsss_dictionary[tracker_id].stable_frames[-1] = True
                    bsss_dictionary[tracker_id].speeds.append(speed)
                    bsss_dictionary[tracker_id].scores.append(score)

            unstable_frames_counter += 1
            end_time = datetime.now()
            if (end_time-start_time).total_seconds() > 300:
                break

        cap.release()

        # Speed outliers deleting
        id_of_max_speed = 1
        max_detected_speed = 0
        violation_registration = False

        for id in bsss_dictionary:
            if len(bsss_dictionary[id].speeds) != 0:
                max_item_speed = np.nanmax(
                    np.array(bsss_dictionary[id].hampel_with_outliers_replacing()))
                if max_item_speed > max_detected_speed:
                    max_detected_speed = max_item_speed
                    id_of_max_speed = id
                violation_registration = violation_registration or check_consecutive_exceeds(bsss_dictionary[id].speeds, permitted_speed, VIOLATION_DURATION*fps)

        # Calculating median
        median_speed = 0
        if bsss_dictionary.get(id_of_max_speed):
            median_speed = round(
                np.nanmedian(np.array(bsss_dictionary[id_of_max_speed].speeds)), 2)

        # Check if there are consecutive frames for VIOLATION_DURATION with violation
        # if no - return, if yes - visual video processing
        print(f'Violation_registration: {violation_registration}')
        if not violation_registration:
            delete_event_clip(event_id)
            return

        # --------------------Visual video processing--------------------

        # Videocapturing
        cap = cv2.VideoCapture(f'/mqtt/speed_estimation/temp/{event_id}.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))

        # Videowriting
        start_time_dmy = start_time.strftime(r'%d.%m.%Y')
        directory = f'/storage/{start_time_dmy}/'
        if not os.path.isdir(directory):
            os.mkdir(directory)

        directory_temp = '/mqtt/speed_estimation/temp'
        camera_name = camera.lower().replace('reg', 'r').replace('cam', 'c')
        start_time_hms = start_time.strftime(r'%H.%M.%S')
        filepath = (f'{directory_temp}/{camera_name}_{start_time_hms}'
                    f'_ср_{median_speed}кмч_{max_detected_speed}кмч.mp4')
        out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

        print(filepath)
        while cap.isOpened():
            # Кадр с камеры
            ret, frame = cap.read()
            if not ret:
                break
            detected_img = frame.copy()

            for id, bsss_item in bsss_dictionary.items():
                bounding_box, stable_frame, speed, score = bsss_item.pop()
                if stable_frame is True:
                    # Draw detections on the frame
                    detected_img = draw_external_detection(
                        detected_img, np.array(bounding_box).astype('int'), score)

                    # Draw speed caption on the frame
                    detected_img = draw_speed_caption(
                        detected_img, np.array(bounding_box).astype('int'), id, speed)

            # Writing frame to file
            out.write(detected_img)  # frame

        cap.release()
        out.release()
        delete_event_clip(event_id)

        # Postprocessing
        set_retain_to_true(event_id)
        set_sub_label(event_id, f'Max speed: {max_detected_speed} km/h')
        codec_change(filepath, directory)

        if os.path.isfile(filepath):
            system_time.sleep(1)
            os.remove(filepath)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('camera')
    parser.add_argument('event_id')
    args = parser.parse_args()

    camera = args.camera
    event_id = args.event_id

    speed_estimator = SpeedEstimator(r'speed_estimation/clips_model.onnx')
    speed_estimator(camera, event_id)
