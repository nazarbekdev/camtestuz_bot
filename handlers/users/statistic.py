import os
import datetime
import requests
import matplotlib.pyplot as plt
import seaborn as sns
from aiogram import types
from loader import dp, bot
from dotenv import load_dotenv

load_dotenv()


API_STATISTIC = os.getenv('API_STATISTIC')


@dp.message_handler(commands=['statistic'])
async def statistic(message: types.Message):
    data = requests.get(API_STATISTIC)
    now = datetime.datetime.now().strftime('%d.%m.%Y')
    if data.status_code == 200:
        one_day = data.json()['one_day_count']
        a_week = data.json()['seven_days_count']
        one_month = data.json()['one_month_count']
        monthly_users = data.json()['monthly_users']

        # Har oylik foydalanuvchilar ma'lumotini ajratib olish
        months = [item["month"][:10] for item in monthly_users]
        counts = [item["count"] for item in monthly_users]

        # Grafikni chizish
        plt.figure(figsize=(10, 6))
        sns.barplot(x=months, y=counts, palette="Blues_d")
        plt.title("Monthly Users Statistics")
        plt.xlabel("Month")
        plt.ylabel("Number of Users")
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Grafikni saqlash
        file_path = "/Users/uzmacbook/Portfolio/Dtm_Pm_bot/handlers/users/monthly_users_statistics.png"  # Fayl nomi
        plt.savefig(file_path)

        lst = ''
        i = 1
        for user in monthly_users:
            month = user['month']
            count = user['count']
            lst += f"{i}. {month[:10]} ➡️ {count}\n"
            i += 1

        static = f"""
        📊 Yangi foydalanuvchilar statistikasi
        
        • 1 kunda: {one_day}
        • 7 kunda: {a_week}
        • 1 oyda: {one_month}
        
    Ushbu statistika joriy sanadan 1 oy ichidagi ma'lumotlar asosida tayyorlandi!

Sana: {now}

📈📉  📈📉  📈📉  📈📉  📈📉  📈📉  📈📉        
                 """

        await message.answer(static)
        await message.answer(f"📊 Oylik Statistika:\n\n{lst}")

        # Rasmni yuborish
        with open(file_path, 'rb') as photo:
            await message.answer_photo(photo)

        # Faylni o‘chirish (ixtiyoriy)
        os.remove(file_path)
    else:
        await message.answer("❌ Statistikani olishda xatolik yuz berdi.")