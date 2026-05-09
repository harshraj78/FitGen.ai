from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.audit import AuditService
from app.services.auth import require_account
from app.services.tenancy import ADMIN_ROLES, require_org_membership


router = APIRouter(prefix="/organizations/{organization_id}/audit-logs", tags=["audit"])


@router.get("", response_model=schemas.Page[schemas.AuditLogOut])
def list_audit_logs(
    organization_id: int,
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    query = db.query(models.AuditLog).filter(models.AuditLog.organization_id == organization_id)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(models.AuditLog.action == action)
    total = query.count()
    logs = query.order_by(desc(models.AuditLog.created_at), desc(models.AuditLog.id)).offset(offset).limit(limit).all()
    audit = AuditService(db)
    return {"items": [audit.serialize(log) for log in logs], "meta": {"limit": limit, "offset": offset, "total": total}}
