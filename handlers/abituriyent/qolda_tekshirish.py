import os
import time
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
USER_INFO_DATA = os.getenv('API_BOT_USER_INFO')
PATCH_URL = os.getenv('API_BOT_USER_PATCH')
CHECK_ABT_URL = os.getenv('API_CHECK_ABT')

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

    url_data = requests.get(f'{USER_INFO_DATA}{message.from_user.id}')

    if url_data.status_code == 200:
        limit = url_data.json()['limit']
        if limit > 0:
            await message.answer("Iltimos, kitob raqamini kiriting:", reply_markup=cancel_button)
            await CheckSheetForm.book_id.set()
        else:
            await message.answer("Sizda yetarlicha limit mavjud emas!\n\n/myself")
    else:
        await message.answer("Server is not running yet!")


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
    checking_msg = await message.answer('♻️ Tekshirilmoqda...')

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
        success_msg = await message.answer("✅ Muvaffaqiyatli tekshirildi!")
        time.sleep(2)
        await checking_msg.delete()
        await success_msg.delete()
        send_file_msg = await message.answer("📥 Fayl yuklanmoqda...")

        # Yuklanadigan faylni API'dan olish
        r = requests.get(CHECK_ABT_URL, stream=True)

        if r.status_code == 200:
            # Javob sarlavhalaridan Content-Disposition ni olish
            content_disposition = r.headers.get('Content-Disposition')
            if content_disposition:
                file_name = content_disposition.split('filename=')[-1].strip('"')
            else:
                file_name = 'downloaded_file.pdf'

            # Faylni saqlash uchun katalogni tekshirish va yaratish
            directory = os.path.dirname(file_name)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)

            # Faylni saqlash
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Xabarlarni o'chirish
            await send_file_msg.delete()

            # Faylni foydalanuvchiga yuborish
            await message.answer_document(open(file_name, 'rb'))

            url_data = requests.get(f'{USER_INFO_DATA}{message.from_user.id}')

            limit = url_data.json()['limit'] - 1
            checked_file = url_data.json()['checked_file'] + 1

            url_patch = os.getenv('API_BOT_USER_PATCH')
            patch_data = requests.patch(f'{url_patch}{message.from_user.id}', data={'limit': limit,
                                                                                    'checked_file': checked_file})

            # Faylni o'chirish
            os.remove(file_name)

        else:
            await message.answer("Faylni yuklab olishda xatolik yuz berdi.")
    else:
        msg = response.json()['message']
        if len(msg) > 40:
            await checking_msg.delete()
            await message.answer(f'🚫 Error: {msg}\n\n/qolda_tekshir')
        else:
            await checking_msg.delete()
            await message.answer(f'🚫 Error: {msg}')

    # Holatni yakunlash
    await state.finish()
