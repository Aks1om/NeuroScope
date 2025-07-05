# main.py
import sys
import asyncio

if sys.platform.startswith("win"):
    from asyncio import WindowsSelectorEventLoopPolicy
    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

from src.di import dp, bot, polling_service

async def main():
    asyncio.create_task(polling_service.run())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
