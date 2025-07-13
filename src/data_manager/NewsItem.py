# src/data_manager/NewsItem.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, validator, field_validator
import json
from src.utils.file_utils import _parse_date

class RawNewsItem(BaseModel):
    # ───── основные поля ───── #
    id:        int
    title:     str
    url:       HttpUrl
    date:      Optional[datetime] = None
    text:      str
    media_ids: List[str] = []
    language:  str
    topic:     str

    _v_date = validator("date", pre=True, always=True, allow_reuse=True)(_parse_date)


class ProcessedNewsItem(BaseModel):
    # ───── всё, что было в raw ───── #
    id:        int
    title:     str
    url:       HttpUrl
    date:      Optional[datetime] = None
    text:      str
    media_ids: List[str] = []
    language:  str
    topic:     str

    # ───── дополнительные флаги ───── #
    suggested: bool = False
    confirmed: bool = False

    # ───── message_id-шники ───── #
    main_mid: int | None = None  # id первого сообщения альбома
    meta_mid: int | None = None  # id meta-поста
    album_mids: List[int] = []  # ВСЕ id альбома (для надёжного удаления)

    _v_date = validator("date", pre=True, always=True, allow_reuse=True)(_parse_date)

    # NEW: превращаем строку JSON → list[int]
    @field_validator("album_mids", mode="before")
    def _v_album(cls, v):
        if v in (None, "", []):
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return []
        return v