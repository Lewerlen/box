import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from db.cache import start_cache_updater
from db.init_db import initialize_database
from handlers.admin_handlers import admin_router
from handlers.user_handlers import user_router


async def main():
    """Основная асинхронная функция для запуска бота."""
    # 1. Настройка логирования для вывода информации в консоль
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    # 2. Загрузка переменных окружения из .env файла
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logging.critical("Токен бота не найден. Проверьте .env файл.")
        return

    # 3. Инициализация базы данных и кэша
    try:
        initialize_database()
        start_cache_updater()
    except Exception as e:
        logging.error(f"Ошибка при инициализации БД или кэша: {e}")
        return

    # 4. Инициализация бота и диспетчера
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()



    # 5. Подключение роутеров
    # Сначала админский, чтобы его фильтр имел приоритет
    dp.include_router(admin_router)
    dp.include_router(user_router)

    # 6. Запуск бота
    logging.info("Запуск бота...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("Бот остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Работа бота прервана.")