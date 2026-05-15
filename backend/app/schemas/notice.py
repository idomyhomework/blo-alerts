from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID
from app.models.notice import NoticeType, NoticeStatus


class NoticeCreateIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    body: str = Field(..., min_length=10, max_length=2000)
    type: NoticeType
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)


class NoticeUpdateIn(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=200)
    body: str | None = Field(None, min_length=10, max_length=2000)
    type: NoticeType | None = None
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)
    publish: bool = False


class NoticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    body: str
    type: NoticeType
    status: NoticeStatus
    lat: float | None
    lng: float | None
    media_keys: list[str] = []
    author_id: UUID | None
    created_at: datetime
    published_at: datetime | None
    archived_at: datetime | None
