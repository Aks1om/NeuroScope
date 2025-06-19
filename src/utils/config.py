# src/utils/config.py
import os
from types import SimpleNamespace
import yaml
from dotenv import load_dotenv
from src.utils.paths import BASE_DIR


def _dict_to_namespace(d: dict) -> SimpleNamespace:
    """
    Рекурсивно преобразует словарь в объект SimpleNamespace для доступа через точки.
    """
    ns = SimpleNamespace()
    for key, value in d.items():
        if isinstance(value, dict):
            setattr(ns, key, _dict_to_namespace(value))
        else:
            setattr(ns, key, value)
    return ns


def load_config(path: str = 'config.yml') -> SimpleNamespace:
    """
    Загружает конфигурацию из YAML и переменные окружения из .env.

    Берёт из .env:
      - TELEGRAM_API_TOKEN
      - TELEGRAM_CHAT_ID
      - PROGGERS_IDS (comma-separated list)
    """
    # Используем BASE_DIR из paths
    dotenv_path = BASE_DIR / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

    # Загружаем YAML-конфиг
    config_path = BASE_DIR / path
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg_dict = yaml.safe_load(f) or {}

    # Переопределяем секцию telegram данными из окружения
    telegram_cfg = cfg_dict.get('telegram', {})
    telegram_cfg['token'] = os.getenv('TELEGRAM_API_TOKEN', telegram_cfg.get('token'))
    telegram_cfg['chat_id'] = os.getenv('MODERATOR_CHAT_ID', telegram_cfg.get('chat_id'))
    cfg_dict['telegram'] = telegram_cfg

    # Переопределяем список проггеров из переменной окружения PROG_IDS
    prog_ids_env = os.getenv('PROG_IDS')
    if prog_ids_env:
        # сразу преобразуем в int
        prog_ids = [
            int(cid.strip())
            for cid in prog_ids_env.split(',')
            if cid.strip()
        ]
    else:
        # если в YAML уже были, то тоже приводим к int
        prog_ids = []

    cfg_dict['prog'] = {'ids': prog_ids}

    # Рекурсивное преобразование в Namespace
    return _dict_to_namespace(cfg_dict)

