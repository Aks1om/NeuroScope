# src/di.py
import os, shutil
import logging
import importlib
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from src.utils.file_utils import *
from src.bot.logger import setup_logger
from src.bot.filter import ProgOrAdminFilter
from src.bot.middleware import LoggingMiddleware, RoleMiddleware, CommandRestrictionMiddleware
from src.bot.handlers.general import router as general_router
from src.bot.handlers.post import get_post_admin_router
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBNewsRepository
from src.utils.paths import *


from src.data_collector.web_scraper_collector import WebScraperCollector
from src.services.collector_service import CollectorService
from src.services.translate_service import TranslateService
from src.services.chat_gpt_service import ChatGPTService
from src.services.processed_service import ProcessedService
from src.services.sending_service import SendingService
from src.services.polling_service import PollingService

# 1) Загрузка конфига и окружения
load_env()
raw_cfg = load_config()
cfg = dict_to_namespace(raw_cfg)

reset           = cfg.settings.reset
poll_interval   = cfg.settings.poll_interval
first_run       = cfg.settings.first_run
use_chatgpt     = cfg.settings.use_chatgpt
raw_limit       = cfg.settings.raw_limit
suggested_chat_id  = cfg.telegram_channels.suggested_chat_id
prog_ids        = set(cfg.users.prog_ids)
admin_ids       = set(cfg.users.admin_ids)

# 1.5) Если в настройках reset=true, очищаем media и удаляем БД
if reset:
    if os.path.isdir(MEDIA_DIR):
        shutil.rmtree(MEDIA_DIR)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    if os.path.isfile(DB):
        os.remove(DB)

# 2) Бот и логгер
bot = Bot(token=get_env("TELEGRAM_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
logger = setup_logger(cfg, bot)

# 3) Dispatcher + middleware
dp = Dispatcher()
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    logger.info("Запуск NeuroScope")
dp.startup.register(on_startup)

dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(RoleMiddleware(prog_ids, admin_ids, suggested_chat_id))
dp.update.middleware(CommandRestrictionMiddleware(prog_ids, suggested_chat_id))

dp.include_router(general_router)                                       # публичные хэндлеры

# 4) Базы и репозитории
db_client      = DuckDBClient(DB)
raw_repo       = DuckDBNewsRepository(db_client, table_name="raw_news")
processed_repo = DuckDBNewsRepository(db_client, table_name="processed_news")

prog_admin_filter = ProgOrAdminFilter(prog_ids, admin_ids)
dp.include_router(get_post_admin_router(processed_repo, prog_admin_filter, cfg))

# 5) Сервисы
web_collector = WebScraperCollector(cfg.source_map, logger)
translate_svc = TranslateService()
collector_svc = CollectorService(
    raw_repo=raw_repo,
    collector=web_collector,
    translate_service=translate_svc,
    logger=logger,
    raw_limit=raw_limit
)

# 6) Перевод + GPT
chatgpt_svc   = ChatGPTService(
    api_key=get_env("OPENAI_API_KEY"),
    proxy_url=get_env("PROXY")
)

processor_svc = ProcessedService(
    raw_repo=raw_repo,
    processed_repo=processed_repo,
    translate_service=translate_svc,
    chat_gpt_service=chatgpt_svc,
    logger=logger,
    use_chatgpt=use_chatgpt
)

sending_svc = SendingService(
    bot=bot,
    chat_id=suggested_chat_id,
    processed_repo=processed_repo,
    logger=logger
)

# 7) Запуск polling-а
polling_service = PollingService(
    collector_service=collector_svc,
    processed_service=processor_svc,
    sending_service=sending_svc,
    bot=bot,
    suggest_group_id=suggested_chat_id,
    interval=poll_interval,
    first_run=first_run,
    logger=logger
)

__all__ = ["bot", "dp", "logger", "cfg", "polling_service"]