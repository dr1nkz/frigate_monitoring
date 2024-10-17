# Frigate

## Первоначальная настройка контейнера

### Запуск контейнера
docker compose build <br/>
docker compose up -d

### Просмотр логов
docker compose logs -f <br/>
Ctrl + C - закрыть

## Настройка Frigate

### Настройка слушателя сообщений
#### .env файл по пути mqtt/
##### Модель для распознавания
MODEL = speed_estimation/clips_model.onnx
##### Адреса FRIGATE и NANOMQ
NANOMQ_ADDRESS = ...
FRIGATE_ADDRESS = ...

#### transform_points.json по пути mqtt/speed_estimation/
##### Опорные точки для определения скорости и макс. скорость
```json
{
    "имя_камеры": {
        "TARGET_WIDTH" : ширина в метрах,
        "TARGET_HEIGHT" : высота в метрах,
        "PERMITTED_SPEED": разрешенная скорость в км/ч,
    }
}
```