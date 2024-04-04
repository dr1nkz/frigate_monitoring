import requests
import json
import yaml


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
