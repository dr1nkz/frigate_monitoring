import asyncio
import logging
import sys
from os import getenv
import multiprocessing


from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import CommandStart, Command


from db import Database


import paho.mqtt.client as mqtt
import json
import requests


# Bot token can be obtained via https://t.me/BotFather
load_dotenv('../.env')
TOKEN = getenv('BOT_TOKEN')

# All handlers should be attached to the Router (or Dispatcher)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
db = Database('users_database.db')
processes = []


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    # await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")
    if message.chat.type == 'private':
        if not db.user_exists(message.from_user.id):
            db.add_user(message.from_user.id)
            await bot.send_message(message.from_user.id, 'Вы зарегистрировались и подписались на уведомления')
        else:
            await bot.send_message(message.from_user.id, 'Вы уже зарегистрированы')


@dp.message(Command('subscribe'))
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/subscribe` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    # await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")
    if message.chat.type == 'private':
        db.set_active(message.from_user.id, 1)
        await bot.send_message(message.from_user.id, 'Вы подписались на уведомления')


@dp.message(Command('unsubscribe'))
async def command_start_handler(message: Message) -> None:
    """
    This handler receives messages with `/unsubscribe` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    # await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")
    if message.chat.type == 'private':
        db.set_active(message.from_user.id, 0)
        await bot.send_message(message.from_user.id, 'Вы отменили подписку на уведомления')


@dp.message(Command('sendall'))
async def send_all(message: Message):
    if message.chat.type == 'private':
        if message.from_user.id == db.get_all_users()[0][0]:
            text = message.text[9:]
            users = db.get_all_users()
            for user in users:
                try:
                    if int(user[1]) == 1:
                        await bot.send_message(user[0], text)
                except:
                    pass

        await bot.send_message(message.from_user.id, 'Рассылка выполнена успешно')


@dp.message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        # Send a copy of the received message
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        # But not all the types is supported to be copied so need to handle it
        await message.answer("Nice try!")


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    # bot = Bot(token=TOKEN, default=DefaultBotProperties(
    #     parse_mode=ParseMode.HTML))
    # And the run events dispatching
    await dp.start_polling(bot)
    # dp.start_polling(bot)


def on_connect(client, userdata, flags, reason_code, properties):
    """
    The callback for when the client receives a CONNACK response from the server.
    """
    print(f"Connected with result code {reason_code}")
    # Subscribing in on_connect()
    client.subscribe("frigate/events")

# def on_connect(client, userdata, flags, reason_code, properties):
#     """
#     The callback for when the client receives a CONNACK response from the server.
#     """
#     print(f"Connected with result code {reason_code}")
#     # Subscribing in on_connect()
#     client.subscribe("frigate/events")


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

    else:
        print(msg.topic+" "+str(msg.payload))

    if end_time is None:
        # event_ids.remove(event_id)
        process = multiprocessing.Process(target=run_speed_estimation)
        process.start()
        processes.append(process)


async def run_speed_estimation():  # cap: cv2.VideoCapture
    """
    Invoke speed estimation process

    :camera: str - camera name
    :event_id: str - id of the event
    :permitted_speed: int - permitted speed to move
    """
    # subprocess.call(['python3', f'speed_estimation/speed_estimation.py',
    #                  camera, event_id, f'{permitted_speed}'])
    # speed_estimator(camera, event_id, permitted_speed, cap)
    my_db = Database('users_database.db')
    my_bot = Bot(token=TOKEN, default=DefaultBotProperties(
        parse_mode=ParseMode.HTML))
    users = my_db.get_all_users()
    for user in users:
        await my_bot.send_message(user[0], 'run_speed_estimation')


# Теперь вызываем asyncio.run() здесь, вне всех остальных функций
if __name__ == "__main__":
    # multiprocessing.set_start_method('spawn')
    # process = multiprocessing.Process(target=main)
    # process.start()

    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message

    # mqttc.connect("nanomq", 1883, 60)
    mqttc.connect("192.168.16.70", 1883, 60)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    mqttc.loop_start()

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
