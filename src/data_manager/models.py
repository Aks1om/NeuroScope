# src/data_manager/models.py

from datetime import datetime
from typing import List, Optional, Dict, Union
from pydantic import BaseModel, HttpUrl, Field

# --------- News Models ---------

class RawNewsItem(BaseModel):
    id:        int
    title:     str
    url:       HttpUrl
    date:      Optional[datetime] = None
    text:      str
    media_ids: List[str] = []
    language:  str
    topic:     str

class ProcessedNewsItem(BaseModel):
    id:        int
    title:     str
    url:       HttpUrl
    date:      Optional[datetime] = None
    text:      str
    media_ids: List[str] = []
    language:  str
    topic:     str
    suggested: bool = False

class SentNewsItem(BaseModel):
    id:        int
    title:     str
    url:       HttpUrl
    date:      Optional[datetime] = None
    text:      str
    media_ids: List[str] = []
    language:  str
    topic:     str
    confirmed: bool = False
    main_message_id: Optional[int] = None
    others_message_ids: List[int] = []



# --------- Config Models ---------

class SourceSpec(BaseModel):
    class_: str = Field(..., alias="class")
    module: Optional[str] = None
    url:    HttpUrl

class TelegramChannels(BaseModel):
    suggested_chat_id: int
    topics: Dict[str, Union[int, str]]

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
