from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

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
