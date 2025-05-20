import asyncio
import logging
import sys
from os import getenv


from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.types import InputFile, BufferedInputFile


from db import Database


# Bot token can be obtained via https://t.me/BotFather
load_dotenv()
TOKEN = getenv('BOT_TOKEN')

# All handlers should be attached to the Router (or Dispatcher)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
db = Database('users_database.db')


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


@dp.message(Command('picture'))
async def send_picture(message: Message):

    from io import BytesIO
    import requests
    event_id = '1735376997.837127-pa51rm'
    url = f'http://192.168.16.70:5000/api/events/{event_id}/thumbnail.jpg'
    response = requests.get(url)
    image_memory = BytesIO(response.content)
    # binary_image_data = image_memory.getvalue()
    # photo = InputFile(binary_image_data, filename="thumbnail.jpg")
    photo = BufferedInputFile(
        file=image_memory.getvalue(),
        filename="thumbnail.jpg"
    )
    if message.chat.type == 'private':
        if message.from_user.id == db.get_all_users()[0][0]:
            users = db.get_all_users()
            for user in users:
                try:
                    if int(user[1]) == 1:
                        chat_id = user[0]
                        await bot.send_photo(chat_id, photo, caption='фотокарточка')
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


# Теперь вызываем asyncio.run() здесь, вне всех остальных функций
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
