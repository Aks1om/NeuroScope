from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)
from src.utils.formatters import format_news_for_telegram
from src.utils.news import NewsItem
from src.utils.config import TELEGRAM_API_TOKEN

MODERATOR_CHAT_ID = -1002857895412  # ID админского чата
TARGET_CHANNEL_ID = '@Test94039084'  # целевой канал


class TelegramBot:
    def __init__(self):
        self.app = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()

    async def send_news_for_review(self, news_item: NewsItem):
        message = format_news_for_telegram(news_item)

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("Опубликовать 🚀", callback_data=f'publish_{news_item.id}')
        ]])

        if message['image_url']:
            await self.app.bot.send_photo(
                chat_id=MODERATOR_CHAT_ID,
                photo=message['image_url'],
                caption=message['text'],
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            await self.app.bot.send_message(
                chat_id=MODERATOR_CHAT_ID,
                text=message['text'],
                parse_mode='Markdown',
                reply_markup=keyboard
            )

    async def publish_news(self, news_item: NewsItem):
        message = format_news_for_telegram(news_item)

        if message['image_url']:
            await self.app.bot.send_photo(
                chat_id=TARGET_CHANNEL_ID,
                photo=message['image_url'],
                caption=message['text'],
                parse_mode='Markdown'
            )
        else:
            await self.app.bot.send_message(
                chat_id=TARGET_CHANNEL_ID,
                text=message['text'],
                parse_mode='Markdown'
            )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data.startswith('publish_'):
            news_id = int(query.data.split('_')[1])

            # Тут твоя логика получения новости из БД по news_id
            news_item = get_news_item_from_db(news_id)

            # Публикуем новость
            await self.publish_news(news_item)

            # Очищаем кнопки, чтобы нельзя было отправить дважды
            await query.edit_message_reply_markup(reply_markup=None)

    def run_bot(self):
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        print("Bot started")
        self.app.run_polling()
