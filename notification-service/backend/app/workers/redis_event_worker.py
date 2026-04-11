from __future__ import annotations

import asyncio
import json
import logging

from redis import asyncio as aioredis
from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models.device_token import DeviceToken
from app.services.email_service import EmailService
from app.services.fcm_service import FCMService
from app.services.notification_log_service import create_log, parse_user_id, update_status


logger = logging.getLogger(__name__)


class RedisEventWorker:
    def __init__(self) -> None:
        self._redis = None
        self._pubsub = None
        self._task: asyncio.Task | None = None
        self._fcm_service = FCMService()
        self._email_service = EmailService()

    async def start(self) -> None:
        self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        await self._pubsub.subscribe(*settings.redis_channel_list)
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Redis worker subscribed to channels: %s", settings.redis_channel_list)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.aclose()

    async def _listen_loop(self) -> None:
        assert self._pubsub is not None

        while True:
            try:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if not message:
                    await asyncio.sleep(0.05)
                    continue

                channel = str(message.get("channel", ""))
                payload = self._parse_payload(message.get("data"))
                await self._handle_event(channel, payload)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error in Redis event loop")

    @staticmethod
    def _parse_payload(raw_data) -> dict:
        if isinstance(raw_data, dict):
            return raw_data
        if isinstance(raw_data, str):
            try:
                loaded = json.loads(raw_data)
                return loaded if isinstance(loaded, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    async def _handle_event(self, channel: str, payload: dict) -> None:
        if channel == "new_message":
            await self._handle_new_message(payload)
            return
        if channel == "message_deleted":
            await self._handle_message_deleted(payload)
            return
        if channel == "user_registered":
            await self._handle_user_registered(payload)
            return
        if channel == "password_reset":
            await self._handle_password_reset(payload)
            return
        if channel in {"friend_request", "friend_accepted"}:
            await self._handle_friend_event(channel, payload)
            return

        logger.warning("Received message on unsupported channel: %s", channel)

    async def _handle_new_message(self, payload: dict) -> None:
        sender_id = str(payload.get("sender_id", ""))
        recipient_ids = payload.get("recipient_ids") or payload.get("member_ids") or []
        title = str(payload.get("title") or "New message")
        body = str(payload.get("body") or payload.get("message") or "You have a new message")

        if not isinstance(recipient_ids, list):
            return

        for recipient_id in recipient_ids:
            recipient_id = str(recipient_id)
            if not recipient_id or recipient_id == sender_id:
                continue
            await self._send_push_with_fail_safe(
                user_id=recipient_id,
                event_type="new_message",
                title=title,
                body=body,
                data={"event": "new_message"},
            )

    async def _handle_message_deleted(self, payload: dict) -> None:
        log_id = str(payload.get("notification_log_id") or "")
        error_msg = payload.get("error_msg")

        if not log_id:
            return

        db = SessionLocal()
        try:
            updated = update_status(db, log_id=log_id, status="deleted", error_msg=error_msg)
            if not updated:
                logger.warning("message_deleted event references unknown log id: %s", log_id)
        finally:
            db.close()

    async def _handle_user_registered(self, payload: dict) -> None:
        email = str(payload.get("email") or "")
        user_id = str(payload.get("user_id") or "")
        verify_link = str(payload.get("verify_link") or "")
        content = f"Welcome to Real-time Chat App. Verify your account: {verify_link}"

        await self._send_email_with_fail_safe(
            user_id=user_id,
            event_type="user_registered",
            to_email=email,
            subject="Verify your account",
            content=content,
        )

    async def _handle_password_reset(self, payload: dict) -> None:
        email = str(payload.get("email") or "")
        user_id = str(payload.get("user_id") or "")
        reset_token = str(payload.get("reset_token") or payload.get("jwt_token") or "")
        reset_link = str(payload.get("reset_link") or "")
        content = f"Use this token to reset your password: {reset_token}\nReset link: {reset_link}"

        await self._send_email_with_fail_safe(
            user_id=user_id,
            event_type="password_reset",
            to_email=email,
            subject="Reset your password",
            content=content,
        )

    async def _handle_friend_event(self, channel: str, payload: dict) -> None:
        target_user_id = str(payload.get("target_user_id") or payload.get("user_id") or "")
        title = "Friend request" if channel == "friend_request" else "Friend accepted"
        body = str(payload.get("message") or title)

        if not target_user_id:
            return

        await self._send_push_with_fail_safe(
            user_id=target_user_id,
            event_type=channel,
            title=title,
            body=body,
            data={"event": channel},
        )

    async def _send_push_with_fail_safe(
        self,
        *,
        user_id: str,
        event_type: str,
        title: str,
        body: str,
        data: dict[str, str],
    ) -> None:
        db = SessionLocal()
        try:
            user_uuid = parse_user_id(user_id)
            tokens = db.execute(
                select(DeviceToken).where(
                    DeviceToken.user_id == user_uuid,
                    DeviceToken.is_active.is_(True),
                )
            ).scalars().all()

            if not tokens:
                create_log(
                    db,
                    user_id=user_id,
                    event_type=event_type,
                    channel="fcm",
                    status="failed",
                    error_msg="No active device token",
                )
                return

            sent = 0
            for token_row in tokens:
                try:
                    await self._fcm_service.send_push(
                        token=token_row.fcm_token,
                        title=title,
                        body=body,
                        data=data,
                    )
                    sent += 1
                except Exception as exc:
                    create_log(
                        db,
                        user_id=user_id,
                        event_type=event_type,
                        channel="fcm",
                        status="failed",
                        error_msg=str(exc),
                    )

            if sent > 0:
                create_log(
                    db,
                    user_id=user_id,
                    event_type=event_type,
                    channel="fcm",
                    status="sent",
                )
        finally:
            db.close()

    async def _send_email_with_fail_safe(
        self,
        *,
        user_id: str,
        event_type: str,
        to_email: str,
        subject: str,
        content: str,
    ) -> None:
        db = SessionLocal()
        try:
            if not to_email:
                create_log(
                    db,
                    user_id=user_id,
                    event_type=event_type,
                    channel="email",
                    status="failed",
                    error_msg="Missing recipient email",
                )
                return

            try:
                await self._email_service.send_email(
                    to_email=to_email,
                    subject=subject,
                    content=content,
                )
                create_log(
                    db,
                    user_id=user_id,
                    event_type=event_type,
                    channel="email",
                    status="sent",
                )
            except Exception as exc:
                create_log(
                    db,
                    user_id=user_id,
                    event_type=event_type,
                    channel="email",
                    status="failed",
                    error_msg=str(exc),
                )
        finally:
            db.close()
