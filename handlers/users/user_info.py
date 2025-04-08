import os
from loader import dp, bot
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from PyPDF2 import PdfReader, PdfWriter
from dotenv import load_dotenv
import requests

load_dotenv()

USER_INFO_DATA = os.getenv('API_BOT_USER_INFO')


# Existing PDFCutStates
class PDFCutStates(StatesGroup):
    waiting_for_pdf = State()
    waiting_for_output_name = State()
    waiting_for_pages = State()


# New states for merging PDFs
class PDFMergeStates(StatesGroup):
    waiting_for_pdfs = State()
    waiting_for_output_name = State()


# Existing cut_pdf_page function
def cut_pdf_page(input_pdf, output_pdf, page_nums):
    pdf_reader = PdfReader(input_pdf)
    pdf_writer = PdfWriter()

    total_pages = len(pdf_reader.pages)
    success = False

    for page_num in page_nums:
        if 1 <= page_num <= total_pages:
            page = pdf_reader.pages[page_num - 1]
            pdf_writer.add_page(page)
            success = True

    if success:
        with open(output_pdf, 'wb') as output_file:
            pdf_writer.write(output_file)
        return True
    return False


# New function to merge multiple PDFs
def merge_pdfs(input_pdfs, output_pdf):
    pdf_writer = PdfWriter()

    for pdf_path in input_pdfs:
        pdf_reader = PdfReader(pdf_path)
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)

    with open(output_pdf, 'wb') as output_file:
        pdf_writer.write(output_file)
    return True


# Existing /page_cut handlers
@dp.message_handler(commands=['page_cut'])
async def start_page_cut(message: types.Message):
    await PDFCutStates.waiting_for_pdf.set()
    await message.reply("Kesmoqchi bo'lgan PDF faylni yuboring.")


@dp.message_handler(content_types=['document'], state=PDFCutStates.waiting_for_pdf)
async def process_pdf(message: types.Message, state: FSMContext):
    if message.document.mime_type == 'application/pdf':
        file_info = await bot.get_file(message.document.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        temp_path = f"temp_{message.from_user.id}.pdf"
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file.getbuffer())

        await state.update_data(input_pdf=temp_path)
        await PDFCutStates.waiting_for_output_name.set()
        await message.reply("Chiqish fayl nomini kiriting (masalan, 'output.pdf')")
    else:
        await message.reply("Iltimos, haqiqiy PDF fayl yuboring.")


@dp.message_handler(state=PDFCutStates.waiting_for_output_name)
async def process_output_name(message: types.Message, state: FSMContext):
    output_name = message.text.strip()
    if not output_name.endswith('.pdf'):
        output_name += '.pdf'

    await state.update_data(output_pdf=output_name)
    await PDFCutStates.waiting_for_pages.set()
    await message.reply("Kerakli sahifa raqamlarini kiriting (masalan, '1,3,5' yoki '2')")


@dp.message_handler(state=PDFCutStates.waiting_for_pages)
async def process_pages(message: types.Message, state: FSMContext):
    try:
        pages_input = [int(x.strip()) for x in message.text.split(',')]
        data = await state.get_data()
        input_pdf = data['input_pdf']
        output_pdf = data['output_pdf']

        await message.reply("PDF faylingiz qayta ishlanmoqda...")

        if cut_pdf_page(input_pdf, output_pdf, pages_input):
            with open(output_pdf, 'rb') as f:
                await message.reply_document(f, caption="Mana sizning tayyor PDF faylingiz")

            os.remove(input_pdf)
            os.remove(output_pdf)
        else:
            await message.reply("Xatolik: Noto'g'ri sahifa raqamlari yoki qayta ishlash muvaffaqiyatsiz yakunlandi.")

        await state.finish()

    except ValueError:
        await message.reply("Iltimos, to'g'ri sahifa raqamlarini kiriting (masalan, '1,3,5')")
    except Exception as e:
        await message.reply(f"Xatolik yuz berdi: {str(e)}")
        await state.finish()


# New /merge_pdfs command
@dp.message_handler(commands=['merge_pdfs'])
async def start_merge_pdfs(message: types.Message, state: FSMContext):
    await PDFMergeStates.waiting_for_pdfs.set()
    await state.update_data(pdf_files=[])  # Initialize empty list for PDFs
    await message.reply("Birlashtirmoqchi bo'lgan barcha PDF fayllarni yuboring. Tugatsangiz, 'done' deb yozing.")


# Handle PDF files for merging
@dp.message_handler(content_types=['document'], state=PDFMergeStates.waiting_for_pdfs)
async def process_merge_pdf(message: types.Message, state: FSMContext):
    if message.document.mime_type == 'application/pdf':
        file_info = await bot.get_file(message.document.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)

        temp_path = f"temp_merge_{message.from_user.id}_{len((await state.get_data()).get('pdf_files', []))}.pdf"
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file.getbuffer())

        # Update state with new PDF path
        data = await state.get_data()
        pdf_files = data.get('pdf_files', [])
        pdf_files.append(temp_path)
        await state.update_data(pdf_files=pdf_files)

        await message.reply("PDF qabul qilindi. Yana PDF yuboring yoki 'done' deb yozing.")
    else:
        await message.reply("Iltimos, haqiqiy PDF fayl yuboring.")


# Handle 'done' command and ask for output name
@dp.message_handler(lambda message: message.text.lower() == 'done', state=PDFMergeStates.waiting_for_pdfs)
async def process_merge_done(message: types.Message, state: FSMContext):
    data = await state.get_data()
    pdf_files = data.get('pdf_files', [])

    if len(pdf_files) < 1:
        await message.reply("Iltimos, kamida bitta PDF fayl yuboring.")
        return

    await PDFMergeStates.waiting_for_output_name.set()
    await message.reply("Birlashtirilgan PDF uchun chiqish fayl nomini kiriting (masalan, 'merged.pdf')")


# Process output name and merge PDFs
@dp.message_handler(state=PDFMergeStates.waiting_for_output_name)
async def process_merge_output_name(message: types.Message, state: FSMContext):
    output_name = message.text.strip()
    if not output_name.endswith('.pdf'):
        output_name += '.pdf'

    data = await state.get_data()
    pdf_files = data.get('pdf_files', [])

    await message.reply("PDF fayllaringiz birlashtirilmoqda...")

    try:
        if merge_pdfs(pdf_files, output_name):
            with open(output_name, 'rb') as f:
                await message.reply_document(f, caption="Mana sizning birlashtirilgan PDF faylingiz")

            # Clean up
            for pdf_file in pdf_files:
                if os.path.exists(pdf_file):
                    os.remove(pdf_file)
            if os.path.exists(output_name):
                os.remove(output_name)
        else:
            await message.reply("Xatolik: PDF fayllarni birlashtirish muvaffaqiyatsiz yakunlandi.")

        await state.finish()

    except Exception as e:
        await message.reply(f"Xatolik yuz berdi: {str(e)}")
        await state.finish()


# Existing /myself handler
@dp.message_handler(commands=['myself'])
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


# Cancel handler
@dp.message_handler(commands=['cancel'], state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Jarayon bekor qilindi.')
