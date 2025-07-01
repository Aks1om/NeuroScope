# src/bot/logger.py
import logging
import sys
import asyncio
from aiogram import Bot

class TelegramLogsHandler(logging.Handler):
    """
    Custom logging handler that sends logs to Telegram:
    - ERROR+ to programmer private chats
    - INFO to a designated group chat
    """
    def __init__(self, bot: Bot, user_ids=None, chat_id=None, level=logging.NOTSET):
        super().__init__(level)
        self.bot = bot
        self.user_ids = user_ids or []
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord):
        try:
            text = self.format(record)
            loop = asyncio.get_event_loop()
            # Errors and above -> private to prog_ids
            if record.levelno >= logging.ERROR and self.user_ids:
                for uid in self.user_ids:
                    loop.create_task(
                        self.bot.send_message(chat_id=uid, text=f"❗️{record.levelname}: {text}")
                    )
            # Info and below -> group chat
            elif record.levelno >= logging.INFO and self.chat_id:
                loop.create_task(
                    self.bot.send_message(chat_id=self.chat_id, text=text)
                )
        except Exception:
            self.handleError(record)


def setup_logger(cfg: dict, bot: Bot) -> logging.Logger:
    """
    Configure the application logger:
    - FileHandler: all logs to .log file
    - StreamHandler: console output
    - TelegramLogsHandler: INFO to group, ERROR to progs
    """
    # Create logger
    logger = logging.getLogger("bot")
    level = logging.DEBUG if cfg.get("debug", False) else logging.INFO
    logger.setLevel(level)

    # Formatter with module name for context
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    # 1) File handler
    log_file = cfg.get("log_file", "bot.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(level)
    logger.addHandler(fh)

    # 2) Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    ch.setLevel(level)
    logger.addHandler(ch)

    # 3) Telegram INFO -> group
    info_handler = TelegramLogsHandler(
        bot=bot,
        chat_id=cfg["telegram_channels"]["moderators_chat_id"],
        level=logging.INFO,
    )
    info_handler.setFormatter(fmt)
    logger.addHandler(info_handler)

    # 4) Telegram ERROR -> progs
    error_handler = TelegramLogsHandler(
        bot=bot,
        user_ids=cfg["users"]["prog_ids"],
        level=logging.ERROR,
    )
    error_handler.setFormatter(fmt)
    logger.addHandler(error_handler)

    return logger