import requests
import json
import yaml
import numpy as np


API_URL = 'http://frigate:5000/api/'


def set_retain_to_true(id: str):
    """
    Set retain to true for the event with matches id

    :id: str - id of the event
    """
    url = f'{API_URL}events/{id}/retain'
    # set star
    response = requests.post(url=url)
    try:
        print(response.json())
    except:
        pass


def set_retain_to_false(id: str):
    """
    Set retain to false for the event with matches id

    :id: str - id of the event
    """
    url = f'{API_URL}events/{id}/retain'
    # remove star
    response = requests.delete(url=url)
    try:
        print(response.json())
    except:
        pass


def set_sub_label(id: str, sublabel: str):
    """
    Set sublabel for the event with matches id

    :id: str - id of the event
    :sublabel: str - sublabel to set to the event
    """
    url = f'{API_URL}events/{id}/sub_label'
    data = {
        "subLabel": sublabel
    }
    # Set sublabel
    response = requests.post(url=url, json=data)
    try:
        print(response.json())
    except:
        pass


def get_camera_address(camera: str, login: str, password: str):
    """
    Get camera address for :camera:

    :camera: str - camera name
    :login: str - login of the camera
    :password: str - password of the camera
    :return: str - camera address
    """
    url = f'{API_URL}config'
    response = requests.get(url=url).text
    response = json.loads(response)
    try:
        address = response["cameras"][camera]['ffmpeg']['inputs'][0]['path']
        address = address.replace('*', login, 1).replace('*', password, 1)
    except:
        address = None

    return address


def get_camera_address_from_config(camera: str):
    """
    Get address of camera

    :camera: str - camera name
    :return: str - camera address
    """
    try:
        with open('/mqtt/config.yml', 'r') as file:
            config = yaml.safe_load(file)
        address = config['cameras'][camera]['ffmpeg']['inputs'][0]['path']
    except:
        address = None

    return address


def get_cameras_names_from_config():
    """
    Get names of cameras

    :return: names - camera names
    """
    try:
        with open('/mqtt/config.yml', 'r') as file:
            config = yaml.safe_load(file)
        names = tuple(config['cameras'].keys())
    except:
        names = None

    return names


def get_end_time(event_id: str):
    """
    Get end time of the event

    :id: str - id of the event
    :return: int - end time of the event
    """
    url = f'{API_URL}events/{event_id}'
    response = requests.get(url=url).text

    try:
        response_json = json.loads(response)
        end_time = response_json['end_time']
    except:
        end_time = None

    return end_time


def get_transform_points(camera: str):
    """
    Get transform points for camera

    :camera: str - camera name
    :return: np.array(int) - transform points for camera
    """
    try:
        with open('speed_estimation/transform_points.json') as file:
            transform_points = json.loads(file.read())

        SOURCE = np.array(transform_points[camera]['SOURCE'])
        TARGET_WIDTH = transform_points[camera]['TARGET_WIDTH'] * 10
        TARGET_HEIGHT = transform_points[camera]['TARGET_HEIGHT'] * 10
        TARGET = np.array([
            [0, 0],
            [TARGET_WIDTH - 1, 0],
            [TARGET_WIDTH - 1, TARGET_HEIGHT - 1],
            [0, TARGET_HEIGHT - 1],
        ])
    except:
        print(f'No transform points for camera \'{camera}\'')
        SOURCE = None
        TARGET = None

    return SOURCE, TARGET


def get_transform_points_from_config(camera: str):
    """
    Get transform points for camera

    :camera: str - camera name
    :return: np.array(int) - transform points for camera
    """
    try:
        url = f'{API_URL}config'
        response = requests.get(url=url).text
        response = json.loads(response)
        source = response["cameras"][camera]['zones']['zone_0']['coordinates']

        source = [int(number) for number in source.split(',')]
        source = np.array(source).reshape(-1, 2).tolist()
        source = sort_rectangle_points(source)

        with open('speed_estimation/transform_points.json') as file:
            transform_points = json.loads(file.read())
        target_width = transform_points[camera]['TARGET_WIDTH'] * 10
        target_height = transform_points[camera]['TARGET_HEIGHT'] * 10
        target = np.array([
            [0, 0],
            [target_width - 1, 0],
            [target_width - 1, target_height - 1],
            [0, target_height - 1],
        ])
    except:
        print(f'No transform points for camera \'{camera}\'')
        source = None
        target = None

    return source, target


def sort_rectangle_points(points):
    # Убедимся, что мы получили именно 4 точки
    if len(points) != 4:
        raise ValueError("Необходимо предоставить ровно 4 точки.")

    # Сначала находим верхнюю левую точку
    top_left = min(points, key=lambda p: (p[0], p[1]))
    points.remove(top_left)

    # Теперь у нас остались 3 точки. Определим их
    # По часовой стрелке от верхней левой точки
    # Относительно верхней левой точки
    def angle_from_top_left(point):
        # Считаем угол относительно линии, проведенной через верхнюю левую точку
        x, y = point[0] - top_left[0], point[1] - top_left[1]
        return (y, -x)  # Поменяли знак на x, так как в системе координат y вниз

    # Сортируем оставшиеся точки по углу
    sorted_points = sorted(points, key=angle_from_top_left)

    # Возвращаем список, начинающийся с верхней левой точки
    return [top_left] + sorted_points
