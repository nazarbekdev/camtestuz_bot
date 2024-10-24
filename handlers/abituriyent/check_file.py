import os
import time

import requests
from aiogram import types
from loader import dp, bot
from dotenv import load_dotenv
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
API_ENDPOINT_ABITURIYENT = os.getenv("API_ABITURIYENT")
API_ENDPOINT_PREZIDENT = os.getenv("API_PREZIDENT_MAKTABI")

user_context = {}

# Asosiy menyu uchun tugmalar
main_menu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_keyboard.add(KeyboardButton("👨🏻‍🎓 Abituriyent"))
main_menu_keyboard.add(KeyboardButton("🤵‍♂️ Prezident Maktabi"))

# Ortga qaytish tugmasi bilan klaviatura
back_button_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
back_button_keyboard.add(KeyboardButton("⬅️ Ortga qaytish"))


# Abituriyent uchun bo'limni tanlash
@dp.message_handler(lambda message: message.text == "👨🏻‍🎓 Abituriyent")
async def process_abituriyent(message: types.Message):
    await message.answer("👨🏻‍🎓 Abituriyent bo'limidasiz!\n\n🏞️ Rasm yuboring!!!", reply_markup=back_button_keyboard)
    user_context[message.from_user.id] = 'abituriyent'


# Prezident Maktabi uchun bo'limni tanlash
@dp.message_handler(lambda message: message.text == "🤵‍♂️ Prezident Maktabi")
async def process_prezident_maktabi(message: types.Message):
    await message.answer("🤵‍♂️ Prezident Maktabi bo'limidasiz!\n\n🎑 Rasm yuboring.", reply_markup=back_button_keyboard)
    user_context[message.from_user.id] = 'prezident_maktabi'


# Ortga qaytish tugmasi ishlashi
@dp.message_handler(lambda message: message.text == "⬅️ Ortga qaytish")
async def process_back_button(message: types.Message):
    await message.answer("🔙 Asosiy menyuga qaytdingiz. Bo'lim tanlang:", reply_markup=main_menu_keyboard)
    user_context.pop(message.from_user.id, None)


# Rasmni qayta ishlash
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    context = user_context.get(user_id)

    if context == 'abituriyent':
        await process_image(message, API_ENDPOINT_ABITURIYENT)
    elif context == 'prezident_maktabi':
        await process_image(message, API_ENDPOINT_PREZIDENT)
    else:
        await message.answer("Iltimos, avval bo'limni tanlang 👇👇👇", reply_markup=main_menu_keyboard)


# Umumiy rasmni qayta ishlash funksiyasi
async def process_image(message: types.Message, api_endpoint):
    checking_msg = await message.answer("️♻️ Tekshirilmoqda...")

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
        user_id = message.from_user.id
        if user_context.get(user_id) == 'abituriyent':
            data = {
                'user': 122,
                'book_id': '',
            }
            url = os.getenv('API_CHECK_ABT')
        else:
            data = {
                'user': 122,
            }
            url = os.getenv('API_CHECK_PM')
        response = requests.post(api_endpoint, files=files, data=data)
    os.remove("check_photo.jpg")

    if response.status_code == 200:
        success_msg = await message.answer("✅ Muvaffaqiyatli tekshirildi!")
        time.sleep(2)
        await checking_msg.delete()
        await success_msg.delete()
        send_file_msg = await message.answer("📥 Fayl yuklanmoqda...")

        # Yuklanadigan faylni API'dan olish
        r = requests.get(url, stream=True)

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
