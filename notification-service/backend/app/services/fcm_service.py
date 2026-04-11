from __future__ import annotations

import asyncio
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, messaging

from app.core.config import settings


class FCMService:
    def __init__(self) -> None:
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        if not settings.fcm_credentials_path:
            raise RuntimeError("FCM credentials are not configured")

        cred_file = Path(settings.fcm_credentials_path)
        if not cred_file.exists():
            raise RuntimeError("FCM credentials file not found")

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(cred_file))
            firebase_admin.initialize_app(cred)

        self._initialized = True

    async def send_push(
        self,
        *,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> str:
        self._ensure_initialized()

        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
        )
        return await asyncio.to_thread(messaging.send, message)
