from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models


OWNER_ROLES = {
    models.OrganizationRole.super_admin.value,
    models.OrganizationRole.gym_owner.value,
}
ADMIN_ROLES = OWNER_ROLES | {models.OrganizationRole.admin.value}
COACH_ROLES = ADMIN_ROLES | {
    models.OrganizationRole.trainer.value,
    models.OrganizationRole.nutritionist.value,
}


def normalize_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="Organization slug must contain letters or numbers")
    return slug


def require_org_membership(
    db: Session,
    organization_id: int,
    account: models.Account,
    allowed_roles: Iterable[str] | None = None,
) -> models.OrganizationMembership:
    membership = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.account_id == account.id,
            models.OrganizationMembership.active.is_(True),
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=403, detail="Account is not a member of this organization")
    if allowed_roles is not None and membership.role not in set(allowed_roles):
        raise HTTPException(status_code=403, detail="Insufficient organization role")
    return membership


def get_org_member(
    db: Session,
    organization_id: int,
    member_id: int,
    account: models.Account,
    allowed_roles: Iterable[str] | None = None,
) -> models.UserProfile:
    membership = require_org_membership(db, organization_id, account, allowed_roles)
    member = (
        db.query(models.UserProfile)
        .filter(
            models.UserProfile.id == member_id,
            models.UserProfile.organization_id == organization_id,
        )
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Organization member not found")
    if membership.role == models.OrganizationRole.trainer.value and member.assigned_trainer_id not in (None, account.id):
        raise HTTPException(status_code=403, detail="Trainer can only access assigned members")
    if membership.role == models.OrganizationRole.nutritionist.value and member.assigned_trainer_id not in (None, account.id):
        raise HTTPException(status_code=403, detail="Nutritionist can only access assigned members")
    if membership.role == models.OrganizationRole.member.value and member.account_id != account.id:
        raise HTTPException(status_code=403, detail="Member can only access their own profile")
    return member


def require_plan_reviewer(db: Session, plan: models.WorkoutPlan, account: models.Account) -> models.OrganizationMembership:
    if not plan.organization_id:
        raise HTTPException(status_code=400, detail="Plan is not attached to an organization")
    return require_org_membership(db, plan.organization_id, account, COACH_ROLES)


def serialize_goal(goal: models.Goal) -> dict:
    return {
        "id": goal.id,
        "organization_id": goal.organization_id,
        "member_id": goal.member_id,
        "created_by_account_id": goal.created_by_account_id,
        "assigned_trainer_id": goal.assigned_trainer_id,
        "goal_type": goal.goal_type,
        "title": goal.title,
        "description": goal.description,
        "status": goal.status,
        "target_value": goal.target_value,
        "current_value": goal.current_value,
        "unit": goal.unit,
        "starts_on": goal.starts_on,
        "target_date": goal.target_date,
        "achieved_at": goal.achieved_at,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
        "progress_pct": goal_progress_pct(goal),
        "projected_completion": projected_completion(goal),
    }


def goal_progress_pct(goal: models.Goal) -> float | None:
    if goal.target_value is None or goal.current_value is None or goal.target_value == 0:
        return None
    return round(max(0, min(1, goal.current_value / goal.target_value)) * 100, 1)


def projected_completion(goal: models.Goal) -> date | None:
    if not goal.starts_on or not goal.target_date or goal.current_value is None or goal.target_value in (None, 0):
        return None
    elapsed_days = max(1, (date.today() - goal.starts_on).days)
    progress = goal.current_value / goal.target_value
    if progress <= 0:
        return None
    projected_total_days = int(elapsed_days / progress)
    return goal.starts_on + (goal.target_date - goal.starts_on) if projected_total_days <= 0 else date.fromordinal(goal.starts_on.toordinal() + projected_total_days)


def write_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: int | None,
    account: models.Account | None = None,
    organization_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        models.AuditLog(
            organization_id=organization_id,
            actor_account_id=account.id if account else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=json.dumps(metadata or {}, sort_keys=True),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
