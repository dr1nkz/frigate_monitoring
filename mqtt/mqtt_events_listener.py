import json
import os
import requests

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()
CAMERAS = os.getenv('CAMERAS').split()
LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')
ZONES = os.getenv('ZONES').split()
LABELS = os.getenv('LABELS').split()
DURATION = int(os.getenv('DURATION'))
MAX_SPEED = int(os.getenv('MAX_SPEED'))


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


def on_connect(client, userdata, flags, reason_code, properties):
    """
    # The callback for when the client receives a CONNACK response from the server.
    """
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect()
    client.subscribe("frigate/events")


def on_message(client, userdata, msg):
    """
    The callback for when a PUBLISH message is received from the server.
    """
    if (msg.topic == 'frigate/events'):
        payload = json.loads(str(msg.payload)[2:-1])

        # Required alues from payload
        id = payload["after"]["id"]
        start_time = payload["after"]["start_time"]
        end_time = payload["after"]["end_time"]
        label = payload["after"]["label"]
        camera = payload["after"]["camera"]
        entered_zones = payload["after"]["entered_zones"]
        sub_label = payload["after"]["sub_label"]

        print(f'{msg.topic} {id} {start_time} {end_time} \
        {label} {camera} {entered_zones}')

        # Unwanted object from camera in zone
        for entered_zone in entered_zones:
            if label in LABELS and camera in CAMERAS and entered_zone in ZONES:
                sublabel_to_set = 'Unwanted object from camera in zone'
                print('Unwanted object from camera in zone')
                set_retain_to_true(id)
                set_sub_label(id, sublabel_to_set)
                break

        # Event longer than stated
        if end_time is not None:
            if end_time - start_time > DURATION:
                sublabel_to_set = 'Event longer than stated'
                print('Event longer than stated')
                set_retain_to_true(id)
                if sub_label is None:
                    set_sub_label(id, sublabel_to_set)

        # Speed estimation
        if end_time is not None:
            # speed_estimation(id)
            print('Speed estimation')
    else:
        print(msg.topic+" "+str(msg.payload))


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

mqttc.connect("nanomq", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
mqttc.loop_forever()
