import os
import requests
from aiogram import types
from loader import dp, bot
from dotenv import load_dotenv
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
API_ENDPOINT = os.getenv("API_ABITURIYENT")


# FSM uchun holatlar
class CheckSheetForm(StatesGroup):
    book_id = State()
    photo = State()


# Inline tugmachalar yaratish
cancel_button = InlineKeyboardMarkup(row_width=1)
cancel_button.insert(InlineKeyboardButton("❌ Tugatish", callback_data="cancel"))


# Bekor qilish komandasi
@dp.callback_query_handler(lambda c: c.data == 'cancel', state='*')
async def cancel_process(callback_query: types.CallbackQuery, state: FSMContext):
    """Jarayonni bekor qilish"""
    await state.finish()
    await callback_query.message.answer("Jarayon bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())
    await callback_query.answer()


# Qo‘shimcha: Timeout uchun middleware
class TimeoutMiddleware(BaseMiddleware):
    async def on_pre_process_update(self, update: types.Update, data: dict):
        # Agar foydalanuvchi yangi xabar yuborsa va avvalgi jarayon to‘xtamagan bo‘lsa
        if update.message:
            state = dp.current_state(chat=update.message.chat.id, user=update.message.from_user.id)
            current_state = await state.get_state()

            if current_state is not None:
                await state.finish()
                await update.message.reply("Oldingi jarayon tugatildi, yangi komandani boshlang.")


@dp.message_handler(commands=['qolda_tekshir'])
async def start_manual_check(message: types.Message):
    await message.answer("Iltimos, kitob raqamini kiriting:", reply_markup=cancel_button)
    await CheckSheetForm.book_id.set()


@dp.message_handler(state=CheckSheetForm.book_id)
async def process_book_id(message: types.Message, state: FSMContext):
    if len(message.text) == 7:
        # Foydalanuvchidan kitob ID'ni qabul qilish
        async with state.proxy() as data:
            data['book_id'] = message.text

        await message.answer("Endi rasmni yuboring:", reply_markup=cancel_button)
        await CheckSheetForm.photo.set()
    else:
        await message.reply("Iltimos, kitobcha raqamini to'g'ri formatda kiriting!", reply_markup=cancel_button)


@dp.message_handler(content_types=['photo'], state=CheckSheetForm.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await message.answer('♻️ Tekshirilmoqda...')

    # Kitob ID'ni olish
    async with state.proxy() as data:
        book_id = data['book_id']

    # Telegram serveridan fayl ma'lumotlarini olish
    file_info = await bot.get_file(message.photo[-1].file_id)

    # Faylni yuklab olish
    downloaded_file = await bot.download_file(file_info.file_path)

    # Faylni vaqtinchalik saqlash
    with open("check_photo.jpg", "wb") as f:
        f.write(downloaded_file.read())

    # API'ga rasmni yuborish
    with open("check_photo.jpg", "rb") as image_file:
        files = {
            'file': image_file,
        }
        data = {
            'user': 122,
            'book_id': book_id,
        }
        response = requests.post(API_ENDPOINT, files=files, data=data)

    os.remove("check_photo.jpg")

    if response.status_code == 200:
        await message.answer("✅ Muvaffaqiyatli tekshirildi!")
    else:
        msg = response.json().get('message', 'Xatolik yuz berdi')
        if len(msg) > 40:
            await message.answer(f'🚫 Error: {msg}\n\n/qolda_tekshir')
        else:
            await message.answer(f'🚫 Error: {msg}')

    # Holatni yakunlash
    await state.finish()


# Middleware ni qo‘llash
# dp.middleware.setup(TimeoutMiddleware())
