FROM python:3.10.12

WORKDIR /mqtt

COPY ./requirements.txt /mqtt

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

# CMD [ "python3", "mqtt_events_listener.py" ]
