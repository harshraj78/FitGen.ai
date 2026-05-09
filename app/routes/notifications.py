from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.auth import require_account
from app.services.notifications import NotificationService
from app.services.tenancy import require_org_membership


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=schemas.Page[schemas.NotificationOut])
def list_notifications(
    organization_id: int | None = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    if organization_id is not None:
        require_org_membership(db, organization_id, account)
    items, total = NotificationService(db).list_for_account(
        account,
        organization_id=organization_id,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": {"limit": limit, "offset": offset, "total": total}}


@router.post("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.Notification:
    notification = db.get(models.Notification, notification_id)
    if not notification or notification.recipient_account_id != account.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    NotificationService(db).mark_read(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.put("/preferences", response_model=dict)
def update_notification_preference(
    payload: schemas.NotificationPreferenceUpdate,
    organization_id: int | None = None,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    if organization_id is not None:
        require_org_membership(db, organization_id, account)
    preference = (
        db.query(models.NotificationPreference)
        .filter(
            models.NotificationPreference.organization_id == organization_id,
            models.NotificationPreference.account_id == account.id,
            models.NotificationPreference.event_type == payload.event_type,
            models.NotificationPreference.channel == payload.channel,
        )
        .first()
    )
    if preference:
        preference.enabled = payload.enabled
    else:
        preference = models.NotificationPreference(
            organization_id=organization_id,
            account_id=account.id,
            event_type=payload.event_type,
            channel=payload.channel,
            enabled=payload.enabled,
        )
        db.add(preference)
    db.commit()
    return {"status": "updated"}
