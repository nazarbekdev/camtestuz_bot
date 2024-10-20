from loader import dp
from aiogram import types
from aiogram.dispatcher.filters.builtin import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


@dp.message_handler(CommandStart())
async def bot_start(message: types.Message):

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    btn_abituriyent = KeyboardButton("👨🏻‍🎓 Abituriyent")
    btn_prezident_maktabi = KeyboardButton("🤵‍♂️ Prezident Maktabi")

    keyboard.add(btn_abituriyent, btn_prezident_maktabi)

    await message.answer(f"Assalomu alaykum, {message.from_user.full_name}!", reply_markup=keyboard)
