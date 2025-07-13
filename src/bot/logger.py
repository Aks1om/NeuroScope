# src/bot/logger.py
from __future__ import annotations
import asyncio
import logging
import sys
from pathlib import Path

from aiogram import Bot

from src.utils.app_config import AppConfig


class TelegramLogsHandler(logging.Handler):
    """
    ERROR+ → в личку программистам
    INFO / WARNING → в группу предложки
    """

    def __init__(self, bot: Bot, prog_ids: set[int], group_chat_id: int | None):
        super().__init__()
        self.bot = bot
        self.prog_ids = prog_ids
        self.group_chat_id = group_chat_id

    def emit(self, record: logging.LogRecord):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # нет активного цикла

        text = self.format(record)

        # ERROR и выше — программистам
        if record.levelno >= logging.ERROR and self.prog_ids:
            for uid in self.prog_ids:
                loop.create_task(
                    self.bot.send_message(chat_id=uid,
                                          text=f"❗️{record.levelname}: {text}")
                )
        # INFO / WARNING — в группу предложки
        elif logging.INFO <= record.levelno < logging.ERROR and self.group_chat_id:
            loop.create_task(
                self.bot.send_message(chat_id=self.group_chat_id, text=text)
            )


def setup_logger(cfg: AppConfig, bot: Bot) -> logging.Logger:
    """
    • DEBUG → stdout + файл
    • INFO/WARNING → stdout + файл + TG-group
    • ERROR+ → stdout + файл + TG-PM devs
    """
    logger = logging.getLogger("bot")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    # ── file ──
    log_file = Path("bot.log")
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # ── console ──
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # ── telegram INFO/WARNING ──
    tg_info = TelegramLogsHandler(
        bot=bot,
        prog_ids=set(),                               # пусто — только в группу
        group_chat_id=cfg.telegram_channels.suggested_chat_id,
    )
    tg_info.setLevel(logging.INFO)
    tg_info.setFormatter(fmt)
    logger.addHandler(tg_info)

    # ── telegram ERROR+ ──
    tg_err = TelegramLogsHandler(
        bot=bot,
        prog_ids=set(cfg.users.prog_ids),
        group_chat_id=None,
    )
    tg_err.setLevel(logging.ERROR)
    tg_err.setFormatter(fmt)
    logger.addHandler(tg_err)

    return logger
