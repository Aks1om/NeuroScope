# src/bot/handlers/prog_private.py
from aiogram import Router
from aiogram.types import Message
from aiogram import F

router = Router()

@router.message(F.chat.type == "private", F.text.startswith("/"))
async def prog_command_handler(message: Message):
    """
    Handle commands from programmers in private chat.
    """
    cmd = message.text.split()[0]
    if cmd == "/status":
        await message.answer("✅ Система запущена и принимает обновления.")
    else:
        await message.answer(f"Неизвестная команда: {cmd}")
