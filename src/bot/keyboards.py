from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_keyboard(post_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{post_id}"),
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{post_id}")
            ]
        ]
    )


def edit_keyboard(pid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Текст", callback_data=f"t:{pid}"),
                InlineKeyboardButton(text="Заголовок", callback_data=f"h:{pid}"),
                InlineKeyboardButton(text="Медиа", callback_data=f"m:{pid}"),
            ],
            [
                InlineKeyboardButton(text="⏪ Откатить", callback_data=f"r:{pid}")
            ],
            [
                InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{pid}")
            ]
        ]
    )

def media_keyboard(post_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Добавить", callback_data=f"media_add:{post_id}"),
                InlineKeyboardButton(text="➖ Удалить", callback_data=f"media_del:{post_id}"),
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data=f"back:{post_id}")
            ]
        ]
    )
