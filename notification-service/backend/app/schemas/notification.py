from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    channel: Literal["in_app", "email", "push"] = "in_app"
    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=2000)


class NotificationOut(NotificationCreate):
    id: str
    is_read: bool
    created_at: datetime


class DeviceTokenUpsert(BaseModel):
    fcm_token: str = Field(..., min_length=20, max_length=512)
    platform: Literal["ios", "android", "web"]


class DeviceTokenDelete(BaseModel):
    fcm_token: str = Field(..., min_length=20, max_length=512)


class DeviceTokenOut(BaseModel):
    id: str
    user_id: str
    fcm_token: str
    platform: str
    is_active: bool


class NotificationLogOut(BaseModel):
    id: str
    user_id: str
    type: str
    channel: str
    status: str
    error_msg: str | None


class NotificationHistoryResponse(BaseModel):
    items: list[NotificationLogOut]
    limit: int
    offset: int
