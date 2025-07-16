# src/bot/middleware.py
from __future__ import annotations
import logging

from aiogram import BaseMiddleware
from aiogram.types import Message


class RoleMiddleware(BaseMiddleware):
    """
    • В личке команды могут слать только `prog_ids`.
    • В группах — только в suggest-chat.
    """
    def __init__(self, prog_ids, admin_ids, suggest_group_id):
        super().__init__()
        self.prog_ids = prog_ids
        self.admin_ids = admin_ids
        self.suggest_group_id = suggest_group_id

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            uid = event.from_user.id
            cid = event.chat.id

            if event.chat.type == "private":
                if uid not in self.prog_ids:
                    return  # молча игнорируем чужие приват-команды
            else:  # group/supergroup
                if cid != self.suggest_group_id:
                    await data["bot"].send_message(
                        cid,
                        "🚫 Команды доступны только в группе-предложке.",
                    )
                    return
        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Записывает каждое обновление на DEBUG-уровне."""
    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    async def __call__(self, handler, event, data):
        #self.logger.debug("Update: %s", event)
        return await handler(event, data)


class CommandRestrictionMiddleware(BaseMiddleware):
    """
    • PRIV: команды могут слать только prog_ids
    • GROUP: команды принимаются только в suggest-chat
    """
    def __init__(self, prog_ids, suggest_group_id):
        super().__init__()
        self.prog_ids = prog_ids
        self.suggest_group_id = suggest_group_id

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.text and event.text.startswith("/"):
            uid = event.from_user.id
            cid = event.chat.id

            if event.chat.type == "private" and uid not in self.prog_ids:
                await data["bot"].send_message(
                    cid,
                    "🚫 Только разработчики могут использовать команды в личке.",
                )
                return

            if event.chat.type != "private" and cid != self.suggest_group_id:
                await data["bot"].send_message(
                    cid,
                    "🚫 Команды доступны только в группе-предложке.",
                )
                return
        return await handler(event, data)
