from aiogram import types


async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand("start", "Botni ishga tushurish"),
            types.BotCommand("myself", "Ma'lumotlarim"),
            types.BotCommand("help", "Yordam"),
            types.BotCommand("qolda_tekshir", "Kitob ID orqali tekshirish"),
        ]
    )
