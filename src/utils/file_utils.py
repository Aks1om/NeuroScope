# src/utils/file_utils.py
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime
from dotenv import load_dotenv

from src.utils.paths import ENV_DIR, CONFIG_DIR
from src.data_manager.models import AppConfig   # ← pydantic-модель


# ─────────────────── env ─────────────────── #
def load_env():
    """Загружает .env в переменные окружения (если файл есть)."""
    load_dotenv(dotenv_path=ENV_DIR)


def get_env(key):
    value = os.environ.get(key)
    if value is None:
        raise RuntimeError(f"ENV: обязательная переменная {key} не найдена!")
    return value


# ─────────────────── config ───────────────── #
def load_app_config(path):
    """Читает config.json и валидирует через Pydantic‐модель AppConfig."""
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return AppConfig.parse_obj(data)

def parse_date(v):
    if v in (None, "", 0):
        return None
    if isinstance(v, datetime):
        return v
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    raise ValueError(f"Неподдерживаемый формат даты: {v!r}")

def make_id(url):
    """MD5(url) → 16 hex → int -> UBIGINT для DuckDB."""
    return int(hashlib.md5(url.encode()).hexdigest()[:16], 16)