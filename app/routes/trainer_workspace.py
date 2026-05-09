from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.auth import require_account
from app.services.tenancy import COACH_ROLES, get_org_member, require_org_membership
from app.services.trainer_workspace import TrainerWorkspaceService


router = APIRouter(prefix="/organizations/{organization_id}/trainer", tags=["trainer-workspace"])


@router.get("/clients", response_model=list[schemas.TrainerClientSummary])
def assigned_clients(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    require_org_membership(db, organization_id, account, COACH_ROLES)
    return TrainerWorkspaceService(db).assigned_clients(organization_id, account.id)


@router.get("/plan-approvals/pending", response_model=list[schemas.PendingPlanApproval])
def pending_plan_approvals(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    require_org_membership(db, organization_id, account, COACH_ROLES)
    return TrainerWorkspaceService(db).pending_plan_approvals(organization_id, account.id)


@router.get("/clients/at-risk", response_model=list[schemas.TrainerClientSummary])
def at_risk_clients(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    require_org_membership(db, organization_id, account, COACH_ROLES)
    return TrainerWorkspaceService(db).at_risk_clients(organization_id, account.id)


@router.get("/clients/{member_id}/progress", response_model=schemas.TrainerClientSummary)
def client_progress_summary(
    organization_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    get_org_member(db, organization_id, member_id, account, COACH_ROLES)
    summary = TrainerWorkspaceService(db).client_progress_summary(organization_id, account.id, member_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Assigned client not found")
    return summary
