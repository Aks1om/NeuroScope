# src/utils/file_utils.py
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime
from dotenv import load_dotenv

from src.utils.paths import ENV_DIR, CONFIG_DIR
from src.utils.app_config import AppConfig   # ← pydantic-модель


# ─────────────────── env ─────────────────── #
def load_env() -> None:
    """Загружает .env в переменные окружения (если файл есть)."""
    load_dotenv(dotenv_path=ENV_DIR)


def get_env(key: str) -> str:
    value = os.environ.get(key)
    if value is None:
        raise RuntimeError(f"ENV: обязательная переменная {key} не найдена!")
    return value


# ─────────────────── config ───────────────── #
def load_app_config(path: Path | str = CONFIG_DIR) -> AppConfig:
    """Читает config.json и валидирует через Pydantic‐модель AppConfig."""
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
    return AppConfig.parse_obj(data)

def _parse_date(v):
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