# src/utils/paths.py
from pathlib import Path

# базовая директория — корень проекта (NeuroScope/)
BASE_DIR = Path(__file__).resolve().parents[2]

# папка для хранения файлов БД
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)

RAW_DB       = DATA_DIR / 'raw_data.duckdb'
PROCESSED_DB = DATA_DIR / 'processed_data.duckdb'

# папка для медиа (изображения, видео и пр.)
MEDIA_DIR = BASE_DIR / 'media'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# папка для хранения моделей нейронных сетей
MODELS_DIR = BASE_DIR / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# пути к модели перевода
EN_RU_ARGOS = MODELS_DIR / 'en_ru.argosmodel'