import os
import base64
import json
import boto3
import paho.mqtt.client as mqtt

# ==== S3 settings ====
AWS_URL = os.getenv('AWS_URL', 'http://minio.emcable.com:9000')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'oPyLxz9a2owX5GBzYIxS')
AWS_SECRET_ACCESS_KEY = os.getenv(
    'AWS_SECRET_ACCESS_KEY', 'xffqAcH5upNjf8K5RZldPWakvVUi5CMxqhOC65Se')
S3_BUCKET = os.getenv('S3_BUCKET', 'test')

# ==== MQTT settings ====
MQTT_BROKER = os.getenv('MQTT_BROKER', '192.168.16.21')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'violations')


def upload_file_to_s3(file_path, bucket_name, object_key):
    s3 = boto3.client(
        's3',
        endpoint_url=AWS_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    try:
        with open(file_path, 'rb') as f:
            s3.upload_fileobj(f, bucket_name, object_key)
        return object_key
    except Exception as e:
        print(f"Ошибка при загрузке файла {file_path} в S3: {e}")
        return None


def send_mqtt_message(filename, start_time, end_time, median_speed, max_detected_speed, duration):
    # Формируем payload для MQTT
    payload = {
        'title': 'Демо нарушение',
        'start_time': start_time,
        'end_time': end_time,
        'median_speed': median_speed,
        'max_detected_speed': max_detected_speed,
        'duration': duration,
        'error_type_codes': [1],
        'description': 'Демо отправка через скрипт',
        'source_data': 'demo_script',
        'extra_data': {'demo': True},
        'file': filename,
    }

    # Отправляем в MQTT
    client = mqtt.Client(callback_api_version=5)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.publish(MQTT_TOPIC, json.dumps(payload))
    print(payload)
    client.disconnect()
    print(f"Данные отправлены в MQTT топик {MQTT_TOPIC}")


def upload_file_to_s3_and_send_mqtt_message(filename, directory, start_time, end_time, median_speed, max_detected_speed, duration):
    file_path = os.path.join(directory, filename)
    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        return
    s3_key = f"demo_uploads/{filename}"
    result_key = upload_file_to_s3(file_path, S3_BUCKET, s3_key)
    if result_key:
        print(f"Загружено: {filename} -> {result_key}")
    else:
        print(f"Ошибка загрузки: {filename}")

    send_mqtt_message(filename, start_time, end_time,
                      median_speed, max_detected_speed, duration)
