# main.py
import sys
import asyncio

if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

from aiogram import Bot
from src.di import dp, bot, polling_service, logger

async def main():
    print("main entry")
    logger.info("Тестовый лог — вывод в консоль и файл должен работать")
    logger.info("Запуск polling_service...")
    asyncio.create_task(polling_service.run())  # стартуем polling_service
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
