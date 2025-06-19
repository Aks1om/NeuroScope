# src/utils/paths.py
from pathlib import Path

# базовая директория — корень проекта (NeuroScope/)
BASE_DIR = Path(__file__).resolve().parents[2]

# папка для хранения файлов БД
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_DB       = DATA_DIR / 'raw_data.duckdb'
PROCESSED_DB = DATA_DIR / 'processed_data.duckdb'

# гарантируем, что файлы существуют
for db in (RAW_DB, PROCESSED_DB):
    db.touch(exist_ok=True)

MEDIA_DIR = BASE_DIR / 'media'
