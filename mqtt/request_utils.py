import requests
import json


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
