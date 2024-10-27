import os
import requests
from loader import dp
from aiogram import types
from dotenv import load_dotenv

load_dotenv()

USER_INFO_DATA = os.getenv('API_BOT_USER_INFO')


@dp.message_handler(commands='myself')
async def bot_help(message: types.Message):
    url_data = requests.get(f'{USER_INFO_DATA}{message.from_user.id}').json()
    data = f"""
👤  {url_data['name']}
🆔  {url_data['telegram_id']}
Limit:  {url_data['limit']}
Jami tekshirilgan fayllar:  {url_data['checked_file']}

Limit yoqish uchun: @mr_uzdev
    """

    await message.answer(data)
