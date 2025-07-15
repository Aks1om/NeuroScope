# src/services/duplicate_filter_service.py
import numpy as np
from sentence_transformers import SentenceTransformer, util
from datetime import datetime, timedelta

class DuplicateFilterService:
    """
    1) filter() — фильтрация только по URL
    2) is_duplicate_content() — проверка на дубликат по содержанию
    3) filter_content() — отбор неповторяющихся по содержанию элементов
    """

    def __init__(
        self,
        repo,
        dub_threshold,
        dub_hours_threshold,
        embedding_model=None,
    ):
        self.repo = repo
        self.dub_threshold = dub_threshold
        self.dub_hours_threshold = dub_hours_threshold
        if embedding_model is not None:
            self._model = embedding_model
        else:
            if not hasattr(DuplicateFilterService, "_model"):
                DuplicateFilterService._model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
            self._model = DuplicateFilterService._model

    def get_recent_texts(self, raw_items, processed_ids):
        cutoff = datetime.utcnow() - timedelta(hours=self.dub_hours_threshold)
        return [
            it.text
            for it in raw_items
            if (it.id in processed_ids and it.date and it.date >= cutoff)
        ]

    def filter(self, items):
        cur = self.repo.conn.execute(f"SELECT url FROM {self.repo.table}")
        existing_urls = {row[0] for row in cur.fetchall()}

        unique = []
        for it in items:
            url = str(it.url)
            if url in existing_urls:
                continue
            existing_urls.add(url)
            unique.append(it)
        return unique

    def is_duplicate_content(self, item):
        cutoff = datetime.utcnow() - timedelta(hours=self.dub_hours_threshold)
        cur = self.repo.conn.execute(
            f"SELECT text FROM {self.repo.table} WHERE date >= ?",
            [cutoff]
        )
        for (existing_text,) in cur.fetchall():
            if self._similarity(item.text, existing_text) >= self.dub_threshold:
                return True
        return False

    def is_similar_recent(self, text, recent_texts):
        if not recent_texts:
            return False

        new_emb = self._embedding(text)
        for old in recent_texts:
            if self._similarity(new_emb, self._embedding(old)) >= self.dub_threshold:
                return True
        return False

    # ─────────────────── helpers (приватные) ─────────────────── #
    def _embedding(self, text):
        parts = [p for p in text.split("\n") if len(p.split()) > 5]
        if not parts:
            parts = [text]
        embs = self._model.encode(parts)
        return embs.mean(axis=0)

    @staticmethod
    def _similarity(a_emb, b_emb):
        return float(util.cos_sim(a_emb, b_emb))