# src/logger/logger.py

import logging
from types import SimpleNamespace
from telegram import Bot
from src.utils.config import load_config


def setup_logger(name: str = None) -> logging.Logger:
    """
    Создаёт логгер с консольным и двумя Telegram-хендлерами:
      - общий для INFO+ в канал,
      - для ошибок в личные чаты проггеров.
    """
    cfg = load_config('config.yml')

    # Уровень логирования
    log_level = getattr(logging, cfg.logging.level.upper(), logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Консольный хендлер
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter(cfg.logging.console_format))
    logger.addHandler(console)

    # Telegram-канал для общих логов
    chan_enabled = getattr(cfg.logging, 'tg_log', False)
    chan_handler = TelegramChannelHandler(
        token=cfg.telegram.token,
        chat_id=cfg.telegram.chat_id,
        enabled=chan_enabled,
        level=log_level
    )
    chan_handler.setFormatter(logging.Formatter(cfg.logging.telegram_format))
    logger.addHandler(chan_handler)

    # Telegram-проггеры для ошибок
    proggers_ids = getattr(cfg, 'proggers', SimpleNamespace(ids=[])).ids
    err_enabled = getattr(cfg.logging, 'tg_error_log', False)
    proggers_handler = TelegramProggersHandler(
        token=cfg.telegram.token,
        chat_ids=proggers_ids,
        enabled=err_enabled,
        level=logging.ERROR
    )
    proggers_handler.setFormatter(logging.Formatter(cfg.logging.telegram_format))
    logger.addHandler(proggers_handler)

    return logger
