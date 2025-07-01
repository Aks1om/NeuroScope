# src/bot/handlers/general.py
from aiogram import Router
from aiogram.types import Message
from aiogram import F

router = Router()

@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer(
        "Привет! Я бот, принимающий предложения и уведомляющий команду.\n"
        "Используйте /help для списка команд."
    )

@router.message(F.text == "/help")
async def help_handler(message: Message):
    await message.answer(
        "/start — запустить бота\n"
        "/help — справка\n"
        "В группе предложка отправляйте свои предложения просто текстом."
    )