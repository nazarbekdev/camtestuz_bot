import os
import time
import requests
from aiogram import types
from loader import dp, bot
from dotenv import load_dotenv
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.misc import subscription
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.config import CHANNEL

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
API_ENDPOINT_ABITURIYENT = os.getenv("API_ABITURIYENT")
API_ENDPOINT_PREZIDENT = os.getenv("API_PREZIDENT_MAKTABI")

API_CHECK_ABT_URL = os.getenv('API_CHECK_ABT')
API_CHECK_PM_URL = os.getenv('API_CHECK_PM')

USER_INFO_DATA = os.getenv('API_BOT_USER_INFO')
PATCH_URL = os.getenv('API_BOT_USER_PATCH')

user_context = {}

# Asosiy menyu uchun tugmalar
main_menu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_keyboard.add(KeyboardButton("👨🏻‍🎓 Abituriyent"))
main_menu_keyboard.add(KeyboardButton("🤵‍♂️ Prezident Maktabi"))

# Ortga qaytish tugmasi bilan klaviatura
back_button_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
back_button_keyboard.add(KeyboardButton("⬅️ Ortga qaytish"))


# Ortga qaytish tugmasi ishlashi
@dp.message_handler(lambda message: message.text == "⬅️ Ortga qaytish")
async def process_back_button(message: types.Message):
    await message.answer("🔙 Asosiy menyuga qaytdingiz. Bo'lim tanlang:", reply_markup=main_menu_keyboard)
    user_context.pop(message.from_user.id, None)


# Obunani tekshirish uchun tugma yaratish
check_subscription_keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton("Obunani tekshirish", callback_data="check_subs")
)


# Foydalanuvchining obuna ekanligini tekshiradigan funksiya
async def is_user_subscribed(user_id):
    for channel in CHANNEL:
        is_subscribed = await subscription.check(user_id=user_id, channel=channel)
        if not is_subscribed:
            return False
    return True


# Abituriyent bo'limi uchun obunani tekshirish
@dp.message_handler(lambda message: message.text == "👨🏻‍🎓 Abituriyent")
async def process_abituriyent(message: types.Message):
    if await is_user_subscribed(message.from_user.id):
        await message.answer("👨🏻‍🎓 Abituriyent bo'limidasiz!\n\n🏞️ Rasm yuboring!!!", reply_markup=back_button_keyboard)
        user_context[message.from_user.id] = 'abituriyent'
    else:
        await message.answer("❗️Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak!",
                             reply_markup=check_subscription_keyboard)


# Prezident Maktabi bo'limi uchun obunani tekshirish
@dp.message_handler(lambda message: message.text == "🤵‍♂️ Prezident Maktabi")
async def process_prezident_maktabi(message: types.Message):
    if await is_user_subscribed(message.from_user.id):
        await message.answer("🤵‍♂️ Prezident Maktabi bo'limidasiz!\n\n🎑 Rasm yuboring.",
                             reply_markup=back_button_keyboard)
        user_context[message.from_user.id] = 'prezident_maktabi'
    else:
        await message.answer("❗️Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak!",
                             reply_markup=check_subscription_keyboard)


# Rasmni qayta ishlash
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    context = user_context.get(user_id)

    url_data = requests.get(f'{USER_INFO_DATA}{user_id}')
    if url_data.status_code == 200:
        limit = url_data.json()['limit']
        if limit > 0:
            if context == 'abituriyent':
                await process_image(message, API_ENDPOINT_ABITURIYENT)
            elif context == 'prezident_maktabi':
                await process_image(message, API_ENDPOINT_PREZIDENT)
            else:
                await message.answer("Iltimos, avval bo'limni tanlang 👇👇👇", reply_markup=main_menu_keyboard)
        else:
            await message.answer('Sizda yetarlicha limit mavjud emas!\n\n/myself')
    else:
        await message.answer('Server is not running yet!')


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
                'user': 12,
                'book_id': '',
            }
            url = API_CHECK_ABT_URL
        else:
            data = {
                'user': 12,
            }
            url = API_CHECK_PM_URL

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
