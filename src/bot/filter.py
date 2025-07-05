from aiogram.filters import BaseFilter
from aiogram.types import Message

class ProgFilter(BaseFilter):
    def __init__(self, prog_ids):
        self.prog_ids = set(prog_ids)
    async def __call__(self, message: Message):
        return message.chat.type == "private" and message.from_user.id in self.prog_ids

class AdminFilter(BaseFilter):
    def __init__(self, admin_ids):
        self.admin_ids = set(admin_ids)
    async def __call__(self, message: Message):
        return message.from_user.id in self.admin_ids

class IsFromSuggestGroup(BaseFilter):
    def __init__(self, group_id):
        self.group_id = group_id
    async def __call__(self, message: Message):
        return message.chat.id == self.group_id
