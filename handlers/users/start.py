import os
import requests
from loader import dp
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):
    name = message.from_user.first_name
    user_name = message.from_user.username
    id = message.from_user.id
    # Userni ro'yxatga olish
    url_post = os.getenv('API_BOT_USER')
    url_get = os.getenv('API_BOT_USER_INFO')
    check_user = requests.get(f'{url_get}{id}')
    if check_user.status_code != 200:
        res = requests.post(url_post, data={'name': name, 'user_name': user_name, 'telegram_id': id})
        print(res.json())
        print(res.status_code)
        if res.status_code == 200:
            keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
            btn_abituriyent = KeyboardButton("👨🏻‍🎓 Abituriyent")
            btn_prezident_maktabi = KeyboardButton("🤵‍♂️ Prezident Maktabi")

            keyboard.add(btn_abituriyent, btn_prezident_maktabi)

            await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!", reply_markup=keyboard)
    else:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        btn_abituriyent = KeyboardButton("👨🏻‍🎓 Abituriyent")
        btn_prezident_maktabi = KeyboardButton("🤵‍♂️ Prezident Maktabi")

        keyboard.add(btn_abituriyent, btn_prezident_maktabi)
        await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!", reply_markup=keyboard)
