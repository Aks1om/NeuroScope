import logging
class TelegramChannelHandler(logging.Handler):
    """
    Хендлер для отправки логов (INFO+) в Telegram-канал.
    """
    def __init__(self, token: str, chat_id: str, enabled: bool = True, level: int = logging.INFO):
        super().__init__(level)
        self.enabled = enabled
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord) -> None:
        if not self.enabled:
            return
        msg = self.format(record)
        try:
            self.bot.send_message(chat_id=self.chat_id, text=msg, parse_mode="Markdown")
        except Exception:
            self.handleError(record)

class TelegramProggersHandler(logging.Handler):
    """
    Хендлер для отправки ошибок (ERROR+) в личные чаты проггеров.
    """
    def __init__(self, token: str, chat_ids: list[str], enabled: bool = True, level: int = logging.ERROR):
        super().__init__(level)
        self.enabled = enabled
        self.bot = Bot(token=token)
        self.chat_ids = chat_ids

    def emit(self, record: logging.LogRecord) -> None:
        if not self.enabled:
            return
        msg = self.format(record)
        for chat_id in self.chat_ids:
            try:
                self.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            except Exception:
                self.handleError(record)
