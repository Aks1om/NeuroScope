# src/bot/filter.py
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from typing import Dict

class ProgFilter(BaseFilter):
    def __init__(self, prog_ids: set[int]):
        self.prog_ids = prog_ids

    async def __call__(self, event: Message | CallbackQuery, data=None) -> bool:
        return event.from_user.id in self.prog_ids

class AdminFilter(BaseFilter):
    """Фильтр, пропускающий апдейты от администраторов."""
    def __init__(self, admin_ids: set[int]):
        # Сохраняем множество админских id
        self.admin_ids = admin_ids

    async def __call__(self, event: Message | CallbackQuery, data=None) -> bool:
        return event.from_user.id in self.admin_ids

class ProgOrAdminFilter(BaseFilter):
    def __init__(self, prog_ids: set[int], admin_ids: set[int]):
        self.allowed_ids = set(prog_ids) | set(admin_ids)

    async def __call__(self, event: Message | CallbackQuery, data=None) -> bool:
        return event.from_user.id in self.allowed_ids

class LockManager:
    """
    Управление локами на редактирование постов в памяти.
    post_id -> user_id
    """
    _locks: Dict[int, int] = {}

    @classmethod
    def lock(cls, post_id: int, user_id: int):
        cls._locks[post_id] = user_id

    @classmethod
    def unlock(cls, post_id: int):
        cls._locks.pop(post_id, None)

    @classmethod
    def is_locked_by_other(cls, post_id: int, user_id: int) -> bool:
        # Истина, если лок есть и он удерживается не этим пользователем
        owner = cls._locks.get(post_id)
        return owner is not None and owner != user_id

class EditingSessionFilter(BaseFilter):
    """
    Фильтр для колбэков/сообщений: разрешает действия только если
    пользователь сейчас владеет локом на соответствующий post_id.
    """
    async def __call__(self, event: CallbackQuery | Message, data=None) -> bool:
        # предполагаем, что data.callback_query.data или event.text содержит "<префикс>:<post_id>"
        payload = event.data  # для CallbackQuery
        pid = int(payload.split(':')[-1])
        return not LockManager.is_locked_by_other(pid, event.from_user.id)