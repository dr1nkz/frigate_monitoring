import json
import os
import requests
import subprocess
import multiprocessing

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

from request_utils import set_retain_to_true, set_sub_label


load_dotenv()
CAMERAS = os.getenv('CAMERAS').split()
ZONES = os.getenv('ZONES').split()
LABELS = os.getenv('LABELS').split()
DURATION = int(os.getenv('DURATION'))
MAX_SPEED = int(os.getenv('MAX_SPEED'))

event_ids = []
processes = []


def run_speed_estimation(camera, event_id, permitted_speed):
    """
    Invoke speed estimation process

    :camera: camera name
    :event_id: id of the event
    :permitted_speed: permitted speed to move
    """
    subprocess.call(['python3', f'speed_estimation/speed_estimation.py',
                     camera, event_id, f'{permitted_speed}'])


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
        event_id = payload["after"]["id"]
        start_time = payload["after"]["start_time"]
        end_time = payload["after"]["end_time"]
        label = payload["after"]["label"]
        camera = payload["after"]["camera"]
        entered_zones = payload["after"]["entered_zones"]
        sub_label = payload["after"]["sub_label"]

        print(f'{msg.topic} {event_id} {start_time} {end_time} \
        {label} {camera} {entered_zones}')

        # Unwanted object from camera in zone
        for entered_zone in entered_zones:
            if label in LABELS and camera in CAMERAS and entered_zone in ZONES:
                sublabel_to_set = 'Unwanted object from camera in zone'
                print('Unwanted object from camera in zone')
                set_retain_to_true(event_id)
                set_sub_label(event_id, sublabel_to_set)
                break

        # Speed estimation
        if (end_time is None) and not (event_id in event_ids):
            event_ids.append(event_id)
            process = multiprocessing.Process(
                target=run_speed_estimation, args=[camera, event_id, MAX_SPEED])
            process.start()
            processes.append(process)

        # Event longer than stated
        if end_time is not None:
            event_ids.remove(event_id)
            if end_time - start_time > DURATION:
                sublabel_to_set = 'Event longer than stated'
                print('Event longer than stated')
                set_retain_to_true(event_id)
                if sub_label is None:
                    set_sub_label(event_id, sublabel_to_set)

    else:
        print(msg.topic+" "+str(msg.payload))

    for i, p in enumerate(processes):
        if p.is_alive():
            continue
        else:
            # Удаляем процесс из списка, если он завершил свою работу
            del processes[i]


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

mqttc.connect("nanomq", 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
mqttc.loop_forever()
