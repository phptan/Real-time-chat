from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, get_db
from app.models.device_token import DeviceToken
from app.models.notification_log import NotificationLog
from app.schemas.notification import (
    DeviceTokenDelete,
    DeviceTokenOut,
    DeviceTokenUpsert,
    NotificationHistoryResponse,
    NotificationLogOut,
)


router = APIRouter()


@router.post("/notifications/device-token", response_model=DeviceTokenOut)
def upsert_device_token(
    payload: DeviceTokenUpsert,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> DeviceTokenOut:
    user_uuid = UUID(user_id)

    existing = db.execute(
        select(DeviceToken).where(DeviceToken.fcm_token == payload.fcm_token)
    ).scalar_one_or_none()

    if existing:
        existing.user_id = user_uuid
        existing.platform = payload.platform
        existing.is_active = True
        token_row = existing
    else:
        token_row = DeviceToken(
            user_id=user_uuid,
            fcm_token=payload.fcm_token,
            platform=payload.platform,
            is_active=True,
        )
        db.add(token_row)

    db.commit()
    db.refresh(token_row)

    return DeviceTokenOut(
        id=str(token_row.id),
        user_id=str(token_row.user_id),
        fcm_token=token_row.fcm_token,
        platform=token_row.platform,
        is_active=token_row.is_active,
    )


@router.delete("/notifications/device-token")
def deactivate_device_token(
    payload: DeviceTokenDelete,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> dict:
    user_uuid = UUID(user_id)

    token_row = db.execute(
        select(DeviceToken).where(
            DeviceToken.user_id == user_uuid,
            DeviceToken.fcm_token == payload.fcm_token,
            DeviceToken.is_active.is_(True),
        )
    ).scalar_one_or_none()

    if token_row:
        token_row.is_active = False
        db.commit()

    return {"status": "ok"}


@router.get("/notifications", response_model=NotificationHistoryResponse)
def get_notification_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> NotificationHistoryResponse:
    user_uuid = UUID(user_id)

    rows = db.execute(
        select(NotificationLog)
        .where(NotificationLog.user_id == user_uuid)
        .order_by(NotificationLog.id.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()

    items = [
        NotificationLogOut(
            id=str(row.id),
            user_id=str(row.user_id),
            type=row.type,
            channel=row.channel,
            status=row.status,
            error_msg=row.error_msg,
        )
        for row in rows
    ]

    return NotificationHistoryResponse(items=items, limit=limit, offset=offset)
