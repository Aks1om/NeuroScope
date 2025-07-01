# src/logger/logger.py
import logging
import sys
import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties


class SingleLevelFilter(logging.Filter):
    """
    Пропускает в хендлер только записи точно указанного уровня.
    """

    def __init__(self, level: int):
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level

class TelegramLogsHandler(logging.Handler):
    def __init__(self, bot: Bot, *, user_ids: list[int] | None = None, chat_id: int | None = None, level: int = logging.NOTSET):
        super().__init__(level)
        self.bot = bot
        self.user_ids = user_ids or []
        self.chat_id = chat_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self.format(record)
            loop = asyncio.get_event_loop()

            if self.chat_id is not None:
                loop.create_task(
                    self.bot.send_message(chat_id=self.chat_id, text=text)
                )

            for uid in self.user_ids:
                loop.create_task(
                    self.bot.send_message(chat_id=uid, text=text)
                )

        except Exception as e:
            print(f"[logger] failed to send tg message: {e}", file=sys.stderr)


def setup_logger(cfg, name: str) -> tuple[logging.Logger, Bot]:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # инициализируем бота с дефолтным HTML-парсингом
    bot = Bot(
        token=cfg.telegram.token,
        default=DefaultBotProperties(parse_mode='HTML')  # ← здесь ключевое изменение
    )

    if cfg.logging.tg_error_log:
        err_h = TelegramLogsHandler(
            bot,
            user_ids=cfg.prog.ids,
            level=logging.ERROR
        )
        err_h.setFormatter(fmt)
        logger.addHandler(err_h)

    if cfg.logging.tg_log:
        info_h = TelegramLogsHandler(
            bot,
            chat_id=cfg.telegram.chat_id,
            level=logging.INFO
        )
        info_h.addFilter(SingleLevelFilter(logging.INFO))
        logger.addHandler(info_h)

    return logger, bot
