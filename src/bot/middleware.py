# src/bot/middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message

class RoleMiddleware(BaseMiddleware):
    def __init__(self, prog_ids: set, manager_ids: set, moderators_chat_id: int):
        super().__init__()
        self.prog_ids = prog_ids
        self.manager_ids = manager_ids
        self.moderators_chat_id = moderators_chat_id

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        chat = getattr(event, "chat", None)
        uid = user.id if user else None
        cid = chat.id if chat else None

        data["is_prog"] = uid in self.prog_ids
        data["is_manager"] = uid in self.manager_ids
        data["is_suggest_group"] = cid == self.moderators_chat_id
        return await handler(event, data)

class LoggingMiddleware(BaseMiddleware):
    def __init__(self, logger):
        super().__init__()
        self.logger = logger

    async def __call__(self, handler, event, data):
        # Log every incoming update
        self.logger.debug(f"Received update: {event!r}")
        return await handler(event, data)

class CommandRestrictionMiddleware(BaseMiddleware):
    """
    Restrict commands:
    - Only prog_ids can send commands in private chat
    - All other commands must be in the suggestion group
    """
    def __init__(self, prog_ids: set, suggest_group_id: int):
        super().__init__()
        self.prog_ids = prog_ids
        self.suggest_group_id = suggest_group_id

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.text and event.text.startswith('/'):
            uid = event.from_user.id
            cid = event.chat.id
            # Private commands -> only progs
            if event.chat.type == "private":
                if uid not in self.prog_ids:
                    await data['bot'].send_message(cid, "🚫 Только программисты могут использовать команды в личных сообщениях.")
                    return
            # Group commands -> only in suggest group
            else:
                if cid != self.suggest_group_id:
                    await data['bot'].send_message(cid, "🚫 Команды доступны только в группе предложка.")
                    return
        return await handler(event, data)