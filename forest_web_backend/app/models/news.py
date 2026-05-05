# app/models/news.py
from pydantic import BaseModel
from typing import Optional

class NewsItem(BaseModel):
    id: str
    title: str
    date: str
    source: str
    content: str
    url: Optional[str] = None

class NewsListResponse(BaseModel):
    data: list[NewsItem]
    total: int