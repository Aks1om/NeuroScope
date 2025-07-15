# src/services/duplicate_filter_service.py
from __future__ import annotations
from typing import List, TypeVar, Generic, Set
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Iterable
# — NLP —
import numpy as np
from sentence_transformers import SentenceTransformer, util

from src.utils.file_utils import load_app_config
from src.data_manager.app_config import AppConfig
from src.data_manager.NewsItem import RawNewsItem
from src.data_manager.duckdb_repository import DuckDBRepository

T = TypeVar("T", bound=BaseModel)


class DuplicateFilterService(Generic[T]):
    """
    1) filter() — фильтрация только по URL
    2) is_duplicate_content() — проверка на дубликат по содержанию
    3) filter_content() — отбор неповторяющихся по содержанию элементов
    """

    def __init__(self, repo: DuckDBRepository):
        self.repo = repo
        cfg: AppConfig = load_app_config()
        self.dub_threshold: float = cfg.settings.dub_threshold
        self.dub_hours_threshold: int = cfg.settings.dub_hours_threshold
        if not hasattr(DuplicateFilterService, "_model"):
            DuplicateFilterService._model: SentenceTransformer = (
                SentenceTransformer("paraphrase-MiniLM-L6-v2")
            )

    def get_recent_texts(
        self,
        raw_items: Iterable[RawNewsItem],
        processed_ids: set[int],
    ) -> list[str]:
        """
        Берёт raw_items и возвращает тексты новостей,
        которые **уже** были переработаны (id ∈ processed_ids)
        и моложе dub_hours_threshold.
        """

        cutoff = datetime.utcnow() - timedelta(hours=self.dub_hours_threshold)
        return [
            it.text
            for it in raw_items
            if (it.id in processed_ids and it.date and it.date >= cutoff)
        ]

    def filter(self, items: List[T]) -> List[T]:
        cur = self.repo.conn.execute(f"SELECT url FROM {self.repo.table}")
        existing_urls: Set[str] = {row[0] for row in cur.fetchall()}

        unique: List[T] = []
        for it in items:
            url = str(it.url)
            if url in existing_urls:
                continue
            existing_urls.add(url)
            unique.append(it)
        return unique

    def is_duplicate_content(self, item: T) -> bool:
        """
        Сравниваем текст `item.text` со всеми text из БД за последние dub_hours_threshold часов.
        Если хоть с одним similarity >= dub_threshold — считаем дубликатом.
        """
        cutoff = datetime.utcnow() - timedelta(hours=self.dub_hours_threshold)
        cur = self.repo.conn.execute(
            f"SELECT text FROM {self.repo.table} WHERE date >= ?",
            [cutoff]
        )
        for (existing_text,) in cur.fetchall():
            if self._similarity(item.text, existing_text) >= self.dub_threshold:
                return True
        return False

    def is_similar_recent(self, text: str, recent_texts: list[str]) -> bool:
        """
        Сравнивает *text* с каждым из *recent_texts* (уже обработанные
        новости за последние N часов).  True ⇢ дубликат по содержанию.
        """
        if not recent_texts:
            return False

        new_emb = self._embedding(text)
        for old in recent_texts:
            if self._similarity(new_emb, self._embedding(old)) >= self.dub_threshold:
                return True
        return False

    # ─────────────────── helpers (приватные) ─────────────────── #
    @classmethod
    def _embedding(cls, text: str) -> np.ndarray:
        """Средний эмбеддинг по абзацам (> 5 слов)."""
        parts = [p for p in text.split("\n") if len(p.split()) > 5]
        if not parts:
            parts = [text]
            embs = cls._model.encode(parts)
        return embs.mean(axis=0)

    @staticmethod
    def _similarity(a_emb: np.ndarray, b_emb: np.ndarray) -> float:
        """Косинусное сходство двух эмбеддингов (0…1)."""
        return float(util.cos_sim(a_emb, b_emb))