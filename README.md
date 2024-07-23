# Frigate

## Первоначальная настройка контейнера

### Запуск контейнера
docker compose build <br/>
docker compose up -d

### Просмотр логов
docker compose logs -f <br/>
Ctrl + C - закрыть

## Настройка Frigate

### Сервис доступен по адресу
http://localhost:5000

### Настройка камеры
Config (меню слева) -> cameras -> <название камеры> -> ffmpeg -> inputs -> - path: <адрес камеры>

### Настройка зон (опорных точек для камеры)
Cameras (меню слева) -> Желаемая камера -> Debug (справа) -> Show options (под изображением с камеры) -> Mask & Zone creator
*Примечание:* важно, чтобы точки были размечены как zone_0.

### Просмотр событий
Events (меню слева), возможна сортировка по Дате, Камере, Виду объекта, Зонам, Саблейблам, Избранным событиям (со звездочками)

## Настройка сервиса по обработке событий и определению скорости

### Настройка слушателя сообщений
#### .env файл по пути mqtt/
##### Если нежелательный объект попал в заданную зону на определенную камеру
CAMERAS = test <br/>
ZONES = zone_1 <br/>
LABELS = no_vest no_hemlet <br/>
##### Если длительность события превышает заданное значение
DURATION = 30 <br/>
##### Максимальная разрешенная скорость
MAX_SPEED = 30 <br/><br/>

#### transform_points.json по пути mqtt/speed_estimation/
##### Координаты для афинных преобразования для определения скорости
```json
{
    "имя_камеры": {
        "TARGET_WIDTH" : ширина в метрах,
        "TARGET_HEIGHT" : высота в метрах,
    }
}
```