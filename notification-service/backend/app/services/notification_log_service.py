from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification_log import NotificationLog


SYSTEM_USER_ID = uuid.UUID(int=0)


def parse_user_id(user_id: str | None) -> uuid.UUID:
    if not user_id:
        return SYSTEM_USER_ID
    try:
        return uuid.UUID(str(user_id))
    except ValueError:
        return SYSTEM_USER_ID


def create_log(
    db: Session,
    *,
    user_id: str | None,
    event_type: str,
    channel: str,
    status: str,
    error_msg: str | None = None,
) -> NotificationLog:
    log_row = NotificationLog(
        user_id=parse_user_id(user_id),
        type=event_type,
        channel=channel,
        status=status,
        error_msg=error_msg,
    )
    db.add(log_row)
    db.commit()
    db.refresh(log_row)
    return log_row


def update_status(
    db: Session,
    *,
    log_id: str,
    status: str,
    error_msg: str | None = None,
) -> bool:
    try:
        row_uuid = uuid.UUID(log_id)
    except ValueError:
        return False

    row = db.execute(select(NotificationLog).where(NotificationLog.id == row_uuid)).scalar_one_or_none()
    if not row:
        return False

    row.status = status
    row.error_msg = error_msg
    db.commit()
    return True
