# src/utils/app_config
from __future__ import annotations
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl


class SourceSpec(BaseModel):
    class_: str = Field(..., alias="class")
    module: Optional[str] = None          # не обязателен
    url:    HttpUrl                       # валидный URL


class TelegramChannels(BaseModel):
    suggested_chat_id: int
    topics: Dict[str, Union[int, str]]    # ← произвольные пары «тема → id/alias»


class UsersBlock(BaseModel):
    prog_ids:  List[int] = []
    admin_ids: List[int] = []


class SettingsBlock(BaseModel):
    reset:         bool = True
    first_run:     bool = True
    use_chatgpt:   bool = True
    test_one_raw:  bool = False
    poll_interval: int = 900
    dub_threshold: float = 0.90
    dub_hours_threshold: int = 6

class AppConfig(BaseModel):
    telegram_channels: TelegramChannels
    users:             UsersBlock
    settings:          SettingsBlock
    source_map:        Dict[str, List[SourceSpec]]

    class Config:
        extra = "forbid"
