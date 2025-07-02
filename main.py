# main.py
import asyncio
from aiogram import Bot
from src.di import dp, bot, polling_service, logger

async def on_startup():
    logger.info("Запуск polling_service...")
    # старт цикла сбора новостей в фоне
    asyncio.create_task(polling_service.run())

async def on_shutdown():
    logger.info("Остановка polling_service...")
    polling_service.stop()
    await bot.session.close()

if __name__ == "__main__":
    # Запуск бота с обработчиками старта и завершения
    asyncio.run(dp.start_polling(
        bot,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    ))
