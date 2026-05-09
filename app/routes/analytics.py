from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.analytics import AnalyticsService
from app.services.auth import require_account
from app.services.tenancy import ADMIN_ROLES, COACH_ROLES, get_org_member, require_org_membership


router = APIRouter(prefix="/organizations/{organization_id}/analytics", tags=["analytics"])


@router.get("/members/{member_id}", response_model=schemas.MemberAnalyticsOut)
def member_analytics(
    organization_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    member = get_org_member(db, organization_id, member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    return AnalyticsService(db).member_analytics(member)


@router.get("/trainers/{trainer_account_id}", response_model=schemas.TrainerAnalyticsOut)
def trainer_analytics(
    organization_id: int,
    trainer_account_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    membership = require_org_membership(db, organization_id, account, COACH_ROLES)
    if membership.role in {models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value} and trainer_account_id != account.id:
        raise HTTPException(status_code=403, detail="Trainer can only view their own analytics")
    return AnalyticsService(db).trainer_analytics(organization_id, trainer_account_id)


@router.get("/gym", response_model=schemas.GymAnalyticsOut)
def gym_analytics(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    return AnalyticsService(db).gym_analytics(organization_id)
