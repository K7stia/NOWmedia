import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties  # 👈 Додано
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from utils.access_control import IsAdmin

# Завантажити змінні з .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Імпортуємо роутери
from routers import (
    main_menu,
    publish,
    groups,
    channel_signature,
    menu_channels,
    admin_panel,
    monitoring_manual,
    monitoring_menu,
    monitoring_rewrite,
    monitoring_categories,
    add_facebook,
)

async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing in .env file!")

    # ✅ Правильне створення бота з parse_mode
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )

    dp = Dispatcher(storage=MemoryStorage())

    # ✅ Глобальні фільтри доступу (тільки для дозволених юзерів)
    dp.message.filter(IsAdmin())
    dp.callback_query.filter(IsAdmin())

    # ✅ Підключення всіх роутерів
    dp.include_router(main_menu.router)
    dp.include_router(publish.router)
    dp.include_router(groups.router)
    dp.include_router(channel_signature.router)
    dp.include_router(menu_channels.router)
    dp.include_router(admin_panel.router)
    dp.include_router(monitoring_manual.router)
    dp.include_router(monitoring_menu.router)
    dp.include_router(monitoring_rewrite.router)
    dp.include_router(monitoring_categories.router)
    dp.include_router(add_facebook.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
