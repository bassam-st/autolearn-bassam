from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchHit(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None
    published: Optional[datetime] = None
    source: Optional[str] = None

class PageDoc(BaseModel):
    url: str
    title: str
    text: str
    published: Optional[datetime] = None
    fetched_at: datetime

class Insight(BaseModel):
    id: Optional[int] = None
    topic: str
    summary: str
    confidence: float = 0.5
    sources: List[str] = Field(default_factory=list)
    created_at: datetime
