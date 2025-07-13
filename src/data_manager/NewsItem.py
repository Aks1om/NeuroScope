# src/data_manager/NewsItem.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, validator

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

    _v_date = validator("date", pre=True, always=True, allow_reuse=True)(_parse_date)
