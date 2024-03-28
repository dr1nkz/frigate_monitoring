import requests


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
