from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from utils import default_expires_at


class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: datetime = Field(default_factory=default_expires_at)


class LinkResponse(BaseModel):
    short_code: str
    original_url: HttpUrl
    expires_at: datetime = Field(default_factory=default_expires_at)


class LinkUpdate(BaseModel):
    original_url: HttpUrl


class LinkStats(BaseModel):
    original_url: HttpUrl
    created_at: datetime
    redirect_count: int
    last_used: Optional[datetime]

