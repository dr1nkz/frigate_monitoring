import requests
import json
import yaml
import numpy as np


API_URL = 'http://frigate:5000/api/'


def set_retain_to_true(id):
    """
    Sets retain to true for the event with matches id
    """
    url = f'{API_URL}events/{id}/retain'
    # set star
    response = requests.post(url=url)
    try:
        print(response.json())
    except:
        pass


def set_retain_to_false(id):
    """
    Sets retain to false for the event with matches id
    """
    url = f'{API_URL}events/{id}/retain'
    # remove star
    response = requests.delete(url=url)
    try:
        print(response.json())
    except:
        pass


def set_sub_label(id, sublabel):
    """
    Sets sublabel for the event with matches id
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


def get_camera_address(camera, login, password):
    """
    Gets camera address for :camera:
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


def get_camera_address_from_config(camera):
    """
    Gets camera address for :camera:
    """
    try:
        with open('/mqtt/config.yml', 'r') as file:
            config = yaml.safe_load(file)
        address = config['cameras'][camera]['ffmpeg']['inputs'][0]['path']
    except:
        address = None

    return address


def get_end_time(event_id):
    """
    Get end time of the event
    """
    url = f'{API_URL}events/{event_id}'
    response = requests.get(url=url).text

    try:
        response_json = json.loads(response)
        end_time = response_json['end_time']
    except:
        end_time = None

    return end_time


def get_transform_points(camera):
    """
    Get transform points for camera
    """
    try:
        with open('speed_estimation/transform_points.json') as file:
            transform_points = json.loads(file.read())

        SOURCE = np.array(transform_points[camera]['SOURCE'])
        TARGET_WIDTH = transform_points[camera]['TARGET_WIDTH']
        TARGET_HEIGHT = transform_points[camera]['TARGET_HEIGHT']
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
