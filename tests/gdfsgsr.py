from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = "7014592821:AAEqfe-sfKGt8QKnCNGpLrqWCVqDiwQT-9M"  # вставь сюда свой токен

async def chat_id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    await update.message.reply_text(f"Chat ID: {chat.id}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("chatid", chat_id_handler))
    print("Bot is running. Type /chatid in any chat where the bot is present.")
    app.run_polling()

if __name__ == "__main__":
    main()
