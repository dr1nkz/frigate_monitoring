FROM python:3.10.12

WORKDIR /mqtt

COPY ./requirements.txt /mqtt

RUN pip install --no-cache-dir -r requirements.txt

# CMD [ "python3", "mqtt_events_listener.py" ]
