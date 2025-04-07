import os
import time
import requests
from aiogram import types
from data.config import CHANNEL
from loader import dp, bot
from dotenv import load_dotenv
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.misc import subscription
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import fitz

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
API_ENDPOINT_ABITURIYENT = os.getenv("API_ABITURIYENT")
API_ENDPOINT_PREZIDENT = os.getenv("API_PREZIDENT_MAKTABI")
API_CHECK_ABT_URL = os.getenv('API_CHECK_ABT')
API_CHECK_PM_URL = os.getenv('API_CHECK_PM')
USER_INFO_DATA = os.getenv('API_BOT_USER_INFO')
PATCH_URL = os.getenv('API_BOT_USER_PATCH')

ADMIN_ID = os.getenv('ADMINS')

user_context = {}

# Asosiy menyu uchun tugmalar
main_menu_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_keyboard.add(KeyboardButton("Abt"))
main_menu_keyboard.add(KeyboardButton("Pm"))

# Ortga qaytish tugmasi bilan klaviatura
back_button_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
back_button_keyboard.add(KeyboardButton("⬅️ Ortga"))

# Obunani tekshirish uchun tugma
check_subscription_keyboard = InlineKeyboardMarkup().add(
    InlineKeyboardButton("Obunani tekshirish", callback_data="check_subs")
)


# PDF faylni rasmlarga aylantirish funksiyasi
def pdf_to_images(pdf_path, output_folder):
    pdf_document = fitz.open(pdf_path)
    image_paths = []
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)
        pix = page.get_pixmap(dpi=150)  # Yuqori sifat uchun DPI
        output_file = f"{output_folder}/page_{page_num + 1}.jpg"
        pix.save(output_file)
        image_paths.append(output_file)
    pdf_document.close()
    return image_paths


# Natija faylini yuklab olish va yuborish funksiyasi
async def download_and_send_result(message: types.Message, url: str, page_num: int):
    try:
        r = requests.get(url, stream=True)
        print(f"API response status code for page {page_num}: {r.status_code}")  # Debugging uchun
        print(f"API response headers for page {page_num}: {r.headers}")  # Debugging uchun
        if r.status_code == 200:
            content_length = int(r.headers.get('Content-Length', 0))
            if content_length == 0:
                await message.answer(f"🚫 Xatolik: API bo‘sh fayl qaytardi (sahifa {page_num})!")
                return False
            file_name = r.headers.get('Content-Disposition', f'filename=page_{page_num}_result.pdf').split('filename=')[
                -1].strip('"')
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            # Faylni yuborishdan oldin uning mavjudligini va hajmini tekshirish
            if os.path.exists(file_name) and os.path.getsize(file_name) > 0:
                await message.answer_document(open(file_name, 'rb'))
                os.remove(file_name)
                return True
            else:
                await message.answer(f"🚫 Xatolik: Yuklangan fayl bo‘sh yoki mavjud emas (sahifa {page_num})!")
                return False
        else:
            await message.answer(
                f"🚫 Faylni yuklab olishda xatolik yuz berdi: Status code {r.status_code} (sahifa {page_num})")
            return False
    except Exception as e:
        await message.answer(f"🚫 Faylni yuklashda xatolik (sahifa {page_num}): {str(e)}")
        return False


# Ortga qaytish tugmasi ishlashi
@dp.message_handler(lambda message: message.text == "⬅️ Ortga")
async def process_back_button(message: types.Message):
    await message.answer("🔙 Asosiy menyuga qaytdingiz. Bo'lim tanlang:", reply_markup=main_menu_keyboard)
    user_context.pop(message.from_user.id, None)


# Foydalanuvchining obuna ekanligini tekshirish
async def is_user_subscribed(user_id):
    for channel in CHANNEL:
        is_subscribed = await subscription.check(user_id=user_id, channel=channel)
        if not is_subscribed:
            return False
    return True


# Abituriyent bo'limi
@dp.message_handler(lambda message: message.text == "Abt")
async def process_abituriyent(message: types.Message):
    if await is_user_subscribed(message.from_user.id):
        await message.answer("Abt bo'limidasiz!\n\nRasm yoki fayl yuboring!", reply_markup=back_button_keyboard)
        user_context[message.from_user.id] = 'abituriyent'
    else:
        await message.answer("❗️Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak!",
                             reply_markup=check_subscription_keyboard)


# Prezident Maktabi bo'limi
@dp.message_handler(lambda message: message.text == "Pm")
async def process_prezident_maktabi(message: types.Message):
    if await is_user_subscribed(message.from_user.id):
        await message.answer("Pm bo'limidasiz!\n\nRasm yoki fayl yuboring!", reply_markup=back_button_keyboard)
        user_context[message.from_user.id] = 'prezident_maktabi'
    else:
        await message.answer("❗️Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak!",
                             reply_markup=check_subscription_keyboard)


# Admin uchun PDF tekshirish komandasi
@dp.message_handler(commands=['check_pdf'])
async def check_pdf_command(message: types.Message):
    if message.from_user.id != int(ADMIN_ID):
        await message.answer("❌ Bu komanda faqat admin uchun mavjud!")
        return
    await message.answer("📄 PDF fayl yuboring, men uni tekshiraman!")


# Admin uchun PDF faylni qayta ishlash
@dp.message_handler(content_types=['document'], user_id=ADMIN_ID)
async def handle_admin_document(message: types.Message):
    user_id = message.from_user.id
    context = user_context.get(user_id)

    if not context:
        await message.answer("Iltimos, avval bo'limni tanlang ('Abt' yoki 'Pm')!")
        return

    # PDF faylni yuklab olish
    file_info = await bot.get_file(message.document.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    pdf_path = "input.pdf"
    with open(pdf_path, "wb") as f:
        f.write(downloaded_file.read())

    # PDFni rasmlarga aylantirish
    output_folder = "temp_images"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    image_paths = pdf_to_images(pdf_path, output_folder)
    await message.answer(f"📄 PDF faylda {len(image_paths)} ta sahifa topildi. Tekshirish boshlanmoqda...")

    # Har bir rasmni tekshirish
    api_endpoint = API_ENDPOINT_ABITURIYENT if context == 'abituriyent' else API_ENDPOINT_PREZIDENT
    url = API_CHECK_ABT_URL if context == 'abituriyent' else API_CHECK_PM_URL

    for idx, image_path in enumerate(image_paths):
        try:
            # Rasmni foydalanuvchiga yuborish
            with open(image_path, "rb") as image_file:
                sent_image = await message.answer_photo(photo=image_file, caption=f"♻️ {idx + 1}-sahifa tekshirilmoqda...")

            # API orqali rasmni tekshirish
            with open(image_path, "rb") as image_file:
                files = {'file': image_file}
                data = {'user': 2, 'book_id': ''} if context == 'abituriyent' else {'user': 2}
                response = requests.post(api_endpoint, files=files, data=data)

            if response.status_code == 200:
                await sent_image.edit_caption(caption=f"✅ {idx + 1}-muvaffaqiyatli tekshirildi!")
                # Har bir sahifa tekshirilgandan so‘ng natija faylini yuklash va yuborish
                success = await download_and_send_result(message, url, idx + 1)
                if not success:
                    await message.answer(f"⚠️ {idx + 1}-sahifa uchun natija faylini yuklab bo‘lmadi.")
            else:
                error_msg = response.json().get('message', 'Nomalum xato')
                # Xatolikni rasmga reply sifatida yuborish
                await sent_image.reply(f"🚫 {idx + 1}-sahifada xatolik: {error_msg}")
            time.sleep(0.2)  # Har bir tekshirish orasida 1 soniya pauza
        except Exception as e:
            await message.reply(f'Xatolik yuzaga keldi: {e}')
            continue

    await message.reply(f"📌Barchasi tekshirildi! Xatolik yuzaga kelgan fayllarni qaytadan tekshirishni ko'rib chiqing!")

    # Vaqtinchalik fayllarni o‘chirish
    for image_path in image_paths:
        if os.path.exists(image_path):
            os.remove(image_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    if os.path.exists(output_folder):
        os.rmdir(output_folder)


# Oddiy foydalanuvchilar uchun hujjat qayta ishlash (faqat rasm qabul qiladi)
@dp.message_handler(content_types=['document'])
async def handle_user_document(message: types.Message):
    await message.answer("❌ Faqat admin PDF fayllarni tekshira oladi. Iltimos, rasm yuboring!")


# Foydalanuvchilar uchun rasm qayta ishlash
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    context = user_context.get(user_id)

    if not context:
        await message.answer("Iltimos, avval bo'limni tanlang 👇👇👇", reply_markup=main_menu_keyboard)
        return

    url_data = requests.get(f'{USER_INFO_DATA}{user_id}')
    if url_data.status_code != 200:
        await message.answer('Server is not running yet!')
        return

    limit = url_data.json()['limit']
    if limit <= 0:
        await message.answer('Sizda yetarlicha limit mavjud emas!\n\n/myself')
        return

    checking_msg = await message.answer("♻️ Tekshirilmoqda...")
    file_info = await bot.get_file(message.photo[-1].file_id)
    downloaded_file = await bot.download_file(file_info.file_path)

    with open("check_photo.jpg", "wb") as f:
        f.write(downloaded_file.read())

    api_endpoint = API_ENDPOINT_ABITURIYENT if context == 'abituriyent' else API_ENDPOINT_PREZIDENT
    url = API_CHECK_ABT_URL if context == 'abituriyent' else API_CHECK_PM_URL

    with open("check_photo.jpg", "rb") as image_file:
        files = {'file': image_file}
        data = {'user': 2, 'book_id': ''} if context == 'abituriyent' else {'user': 2}
        response = requests.post(api_endpoint, files=files, data=data)

    os.remove("check_photo.jpg")

    if response.status_code == 200:
        await checking_msg.edit_text("✅ Muvaffaqiyatli tekshirildi!")
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            file_name = r.headers.get('Content-Disposition', 'filename=result.pdf').split('filename=')[-1].strip('"')
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            await message.answer_document(open(file_name, 'rb'))
            limit -= 1
            checked_file = url_data.json()['checked_file'] + 1
            requests.patch(f'{PATCH_URL}{user_id}', data={'limit': limit, 'checked_file': checked_file})
            os.remove(file_name)
        else:
            await checking_msg.edit_text("Faylni yuklab olishda xatolik yuz berdi.")
    else:
        await checking_msg.edit_text(f"🚫 Xatolik: {response.json().get('message', 'Nomalum xato')}")
