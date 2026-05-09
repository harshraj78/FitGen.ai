from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app import models


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        action: str,
        entity_type: str,
        entity_id: int | None,
        *,
        organization_id: int | None = None,
        actor_account: models.Account | None = None,
        actor_user: models.UserProfile | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> models.AuditLog:
        log = models.AuditLog(
            organization_id=organization_id,
            actor_account_id=actor_account.id if actor_account else None,
            actor_user_id=actor_user.id if actor_user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=json.dumps(metadata or {}, sort_keys=True),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.db.add(log)
        return log

    def serialize(self, log: models.AuditLog) -> dict[str, Any]:
        return {
            "id": log.id,
            "organization_id": log.organization_id,
            "actor_account_id": log.actor_account_id,
            "actor_user_id": log.actor_user_id,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "metadata": _loads(log.metadata_json),
            "created_at": log.created_at,
        }


def _loads(value: str) -> dict[str, Any]:
    try:
        loaded = json.loads(value or "{}")
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        return {}
