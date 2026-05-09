from __future__ import annotations

import re
from datetime import date
from typing import Iterable

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.services.auth import require_account
from app.services.audit import AuditService


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


def org_member_query(db: Session, organization_id: int):
    return db.query(models.UserProfile).filter(models.UserProfile.organization_id == organization_id)


def org_workout_plan_query(db: Session, organization_id: int):
    return db.query(models.WorkoutPlan).filter(models.WorkoutPlan.organization_id == organization_id)


def org_goal_query(db: Session, organization_id: int):
    return db.query(models.Goal).filter(models.Goal.organization_id == organization_id)


def account_can_access_member(membership: models.OrganizationMembership, account: models.Account, member: models.UserProfile) -> bool:
    if membership.role in COACH_ROLES:
        if membership.role in {models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value}:
            return member.assigned_trainer_id in (None, account.id)
        return True
    if membership.role == models.OrganizationRole.member.value:
        return member.account_id == account.id
    return False


def require_roles(allowed_roles: Iterable[str] | None = None):
    def dependency(
        organization_id: int,
        db: Session = Depends(get_db),
        account: models.Account = Depends(require_account),
    ) -> models.OrganizationMembership:
        return require_org_membership(db, organization_id, account, allowed_roles)

    return dependency


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
    if not account_can_access_member(membership, account, member):
        raise HTTPException(status_code=403, detail="Account cannot access this organization member")
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
    AuditService(db).record(
        action,
        entity_type,
        entity_id,
        actor_account=account,
        organization_id=organization_id,
        metadata=metadata,
    )
