from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def emit(
        self,
        event_type: str,
        title: str,
        message: str,
        *,
        organization_id: int | None,
        recipient_account_id: int | None = None,
        recipient_user_id: int | None = None,
        entity_type: str,
        entity_id: int | None,
        payload: dict[str, Any] | None = None,
        channels: list[str] | None = None,
    ) -> models.Notification:
        event = models.NotificationEvent(
            organization_id=organization_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=json.dumps(payload or {}, sort_keys=True),
        )
        self.db.add(event)
        self.db.flush()
        requested_channels = channels or [models.NotificationChannel.in_app.value]
        notifications: list[models.Notification] = []
        for channel in requested_channels:
            notification = models.Notification(
                organization_id=organization_id,
                event_id=event.id,
                recipient_account_id=recipient_account_id,
                recipient_user_id=recipient_user_id,
                event_type=event_type,
                channel=channel,
                title=title,
                message=message,
            )
            self.db.add(notification)
            notifications.append(notification)
        return notifications[0]

    def list_for_account(
        self,
        account: models.Account,
        *,
        organization_id: int | None = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[models.Notification], int]:
        query = self.db.query(models.Notification).filter(models.Notification.recipient_account_id == account.id)
        if organization_id is not None:
            query = query.filter(models.Notification.organization_id == organization_id)
        if unread_only:
            query = query.filter(models.Notification.read_at.is_(None))
        total = query.count()
        items = query.order_by(desc(models.Notification.created_at), desc(models.Notification.id)).offset(offset).limit(limit).all()
        return items, total

    def mark_read(self, notification: models.Notification) -> models.Notification:
        if notification.read_at is None:
            notification.read_at = datetime.utcnow()
        return notification
