import logging
import sys
import asyncio
from aiogram import Bot

class TelegramLogsHandler(logging.Handler):
    """
    Custom logging handler that sends logs to Telegram:
    - ERROR and above -> private messages to prog_ids
    - INFO and WARNING -> group chat
    """
    def __init__(self, bot: Bot, prog_ids=None, group_chat_id=None):
        super().__init__()
        self.bot = bot
        self.prog_ids = set(prog_ids or [])
        self.group_chat_id = group_chat_id

    def emit(self, record: logging.LogRecord):
        try:
            text = self.format(record)
            # Get running loop; if none, skip
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return

            # ERROR and above -> private to programmers
            if record.levelno >= logging.ERROR and self.prog_ids:
                for uid in self.prog_ids:
                    loop.create_task(
                        self.bot.send_message(chat_id=uid, text=f"❗️{record.levelname}: {text}")
                    )
            # INFO and WARNING -> group chat
            elif logging.INFO <= record.levelno < logging.ERROR and self.group_chat_id:
                loop.create_task(
                    self.bot.send_message(chat_id=self.group_chat_id, text=text)
                )
        except Exception:
            self.handleError(record)


def setup_logger(cfg, bot) -> logging.Logger:
    """
    Configure application logger:
    - FileHandler: all logs to a file
    - StreamHandler: console output
    - TelegramLogsHandler: INFO/WARNING to group, ERROR+ to programmers
    """
    logger = logging.getLogger("bot")
    level = logging.DEBUG
    logger.setLevel(level)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    # File handler
    log_file = getattr(cfg, 'log_file', 'bot.log')
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Telegram handler: INFO/WARNING to group
    group_chat_id = None
    if hasattr(cfg, 'telegram_channels'):
        group_chat_id = getattr(cfg.telegram_channels, 'suggested_chat_id', None)
    info_handler = TelegramLogsHandler(
        bot=bot,
        prog_ids=[],
        group_chat_id=group_chat_id
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    logger.addHandler(info_handler)

    # Telegram handler: ERROR+ to programmers
    prog_ids = []
    if hasattr(cfg, 'users'):
        prog_ids = getattr(cfg.users, 'prog_ids', [])
    error_handler = TelegramLogsHandler(
        bot=bot,
        prog_ids=prog_ids,
        group_chat_id=None
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    return logger
