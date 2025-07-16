from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def main_keyboard(post_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{post_id}"),
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm:{post_id}"),
                InlineKeyboardButton(text="⏪ Откатить", callback_data=f"revert:{post_id}"),
            ]
        ]
    )

def edit_keyboard(post_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Текст", callback_data=f"text:{post_id}"),
                InlineKeyboardButton(text="Заголовок", callback_data=f"title:{post_id}"),
                InlineKeyboardButton(text="Медиа", callback_data=f"media:{post_id}"),
            ],
            [
                InlineKeyboardButton(text="✅ Готово", callback_data=f"done:{post_id}")
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
