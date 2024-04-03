import requests
import json
import yaml


def set_retain_to_true(id):
    """
    Sets retain to true for the event with matches id
    """
    url = f'http://frigate:5000/api/events/{id}/retain'
    # set star
    response = requests.post(url=url)
    # remove star
    # response = requests.delete(url=url)
    print(response.json())


def set_sub_label(id, sublabel):
    """
    Sets sublabel for the event with matches id
    """
    url = f'http://frigate:5000/api/events/{id}/sub_label'
    data = {
        "subLabel": sublabel
    }
    # Set sublabel
    response = requests.post(url=url, json=data)
    print(response.json())


def get_camera_address(camera, login, password):
    """
    Gets camera address for :camera:
    """
    response = requests.get(r'http://frigate:5000/api/config').text
    response = json.loads(response)
    address = response["cameras"][camera]['ffmpeg']['inputs'][0]['path']
    address = address.replace('*', login, 1).replace('*', password, 1)

    return address


def get_camera_address_from_config(camera):
    """
    Gets camera address for :camera:
    """
    with open('/mqtt/config.yml', 'r') as file:
        config = yaml.safe_load(file)

    try:
        address = config['cameras'][camera]['ffmpeg']['inputs'][0]['path']
    except:
        address = None

    return address


def get_end_time(event_id):
    """
    Get end time of the event
    """
    response = requests.get(
        f'http://frigate:5000/api/events/{event_id}').text
    response_json = json.loads(response)
    end_time = response_json['end_time']

    return end_time
