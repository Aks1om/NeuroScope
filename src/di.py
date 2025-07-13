# src/di.py
from __future__ import annotations

# ────────────── 0. stdlib / сторонние ────────────── #
import os
import shutil
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ────────────── 1. util-слой ────────────── #
from src.utils.file_utils import load_env, load_app_config
from src.utils.app_config import AppConfig
from src.utils.paths import DB, MEDIA_DIR
from src.bot.logger import setup_logger
from src.bot.filter import ProgOrAdminFilter
from src.bot.middleware import (
    LoggingMiddleware,
    RoleMiddleware,
    CommandRestrictionMiddleware,
)
from src.bot.handlers.general import router as general_router
from src.bot.handlers.post import build_post_admin_router

# ────────────── 2. модели / БД ────────────── #
from src.data_manager.NewsItem import RawNewsItem, ProcessedNewsItem
from src.data_manager.duckdb_client import DuckDBClient
from src.data_manager.duckdb_repository import DuckDBRepository

# ────────────── 3. сервис-слой ────────────── #
from src.services.duplicate_filter_service import DuplicateFilterService
from src.services.media_service import MediaService
from src.services.translate_service import TranslateService
from src.services.chat_gpt_service import ChatGPTService
from src.services.collector_service import CollectorService
from src.services.processed_service import ProcessedService
from src.services.sending_service import SendingService
from src.services.polling_service import PollingService

from src.data_collector.web_scraper_collector import WebScraperCollector

# ────────────── 4. конфиг + окружение ────────────── #
load_env()                                   # .env → os.environ
CFG: AppConfig = load_app_config("config.json")

# ────────────── 5. подготовка файловой среды ────────────── #
if CFG.settings.reset:
    Path(DB).unlink(missing_ok=True)
    if MEDIA_DIR.exists():
        shutil.rmtree(MEDIA_DIR)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# ────────────── 6. бот, логгер, диспетчер ────────────── #
bot = Bot(
    token=os.environ["TELEGRAM_TOKEN"],
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
logger = setup_logger(CFG, bot)

dp = Dispatcher()
dp.update.middleware(LoggingMiddleware(logger))
dp.update.middleware(
    RoleMiddleware(
        CFG.users.prog_ids,
        CFG.users.admin_ids,
        CFG.telegram_channels.suggested_chat_id,
    )
)
dp.update.middleware(
    CommandRestrictionMiddleware(
        CFG.users.prog_ids,
        CFG.telegram_channels.suggested_chat_id,
    )
)
dp.include_router(general_router)

# ────────────── 7. БД и репозитории ────────────── #
db_client      = DuckDBClient(DB)
raw_repo       = DuckDBRepository(db_client.conn, "raw_news",       RawNewsItem)
processed_repo = DuckDBRepository(db_client.conn, "processed_news", ProcessedNewsItem)

# ────────────── 8. сервисы ────────────── #
prog_admin_filter = ProgOrAdminFilter(
    set(CFG.users.prog_ids), set(CFG.users.admin_ids)
)
dp.include_router(build_post_admin_router(processed_repo, prog_admin_filter, CFG))

translate_svc = TranslateService()
media_svc     = MediaService(logger)
dup_raw       = DuplicateFilterService(raw_repo)
dup_proc      = DuplicateFilterService(processed_repo)

web_collector = WebScraperCollector(CFG.source_map, logger)

collector_service = CollectorService(
    raw_repo          = raw_repo,
    collector         = web_collector,
    translate_service = translate_svc,
    media_service     = media_svc,
    duplicate_filter  = dup_raw,
    logger            = logger,
    test_one_raw      = CFG.settings.test_one_raw,
)

chatgpt_service = ChatGPTService(
    api_key  = os.environ.get("OPENAI_API_KEY"),
    proxy_url= os.environ.get("PROXY"),
)

processed_service = ProcessedService(
    raw_repo          = raw_repo,
    processed_repo    = processed_repo,
    translate_service = translate_svc,
    chat_gpt_service  = chatgpt_service,
    duplicate_filter  = dup_proc,
    logger            = logger,
    use_chatgpt       = CFG.settings.use_chatgpt,
)

sending_service = SendingService(
    bot            = bot,
    chat_id        = CFG.telegram_channels.suggested_chat_id,
    processed_repo = processed_repo,
    logger         = logger,
)

polling_service = PollingService(
    collector_service = collector_service,
    processed_service = processed_service,
    sending_service   = sending_service,
    bot               = bot,
    suggest_group_id  = CFG.telegram_channels.suggested_chat_id,
    interval          = CFG.settings.poll_interval,
    first_run         = CFG.settings.first_run,
    logger            = logger,
)

# ────────────── 9. экспорт ────────────── #
__all__ = ["bot", "dp", "polling_service", "CFG", "logger"]
