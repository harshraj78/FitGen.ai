from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.auth import require_account
from app.services.business_ops import (
    BusinessDashboardService,
    RetentionAutomationService,
    RetentionIntelligenceService,
    RevenueOperationsService,
    TrainerPerformanceService,
    TransformationService,
)
from app.services.tenancy import ADMIN_ROLES, COACH_ROLES, get_org_member, require_org_membership, write_audit


router = APIRouter(prefix="/organizations/{organization_id}/business", tags=["business-operations"])


@router.get("/dashboard", response_model=schemas.BusinessDashboardOut)
def owner_dashboard(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    return BusinessDashboardService(db).owner_dashboard(organization_id)


@router.get("/retention/renewal-risk", response_model=list[schemas.RenewalRiskOut])
def at_risk_renewals(
    organization_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    return RetentionIntelligenceService(db).at_risk_renewals(organization_id, limit=min(max(limit, 1), 100))


@router.get("/retention/forecast", response_model=schemas.RenewalForecastOut)
def renewal_forecast(
    organization_id: int,
    window_days: int = 30,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    return RetentionIntelligenceService(db).renewal_forecast(organization_id, window_days=min(max(window_days, 1), 180))


@router.post("/retention/risks/refresh", response_model=list[schemas.RenewalRiskOut])
def refresh_renewal_risks(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    service = RetentionIntelligenceService(db)
    members = db.query(models.UserProfile).filter(models.UserProfile.organization_id == organization_id).all()
    risks = [service.snapshot_member_risk(member) for member in members]
    write_audit(db, "renewal_risk.refreshed", "organization", organization_id, account, organization_id, {"members_scored": len(risks)})
    db.commit()
    return sorted(risks, key=lambda item: item["score"], reverse=True)


@router.get("/revenue", response_model=schemas.RevenueOperationsOut)
def revenue_operations(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    return RevenueOperationsService(db).dashboard(organization_id)


@router.get("/trainers/performance", response_model=schemas.TrainerPerformanceComparisonOut)
def trainer_performance_comparison(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    return TrainerPerformanceService(db).comparison(organization_id)


@router.get("/trainers/{trainer_account_id}/performance", response_model=schemas.TrainerPerformanceOut)
def trainer_performance(
    organization_id: int,
    trainer_account_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    membership = require_org_membership(db, organization_id, account, COACH_ROLES)
    if membership.role in {models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value} and trainer_account_id != account.id:
        raise HTTPException(status_code=403, detail="Trainer can only view their own performance")
    return TrainerPerformanceService(db).trainer_performance(organization_id, trainer_account_id)


@router.get("/actions/today", response_model=schemas.OperationalDailyActionsOut)
def daily_actions(
    organization_id: int,
    persist: bool = False,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    membership = require_org_membership(db, organization_id, account, COACH_ROLES)
    trainer_scope = account.id if membership.role in {models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value} else None
    result = RetentionAutomationService(db).daily_actions(organization_id, persist=persist, trainer_account_id=trainer_scope)
    if persist:
        write_audit(db, "retention_actions.generated", "organization", organization_id, account, organization_id, {"actions": len(result["actions"])})
        db.commit()
    return result


@router.get("/actions/by-type/{workflow_type}", response_model=schemas.OperationalDailyActionsOut)
def daily_actions_by_type(
    organization_id: int,
    workflow_type: str,
    persist: bool = False,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    allowed_types = {item.value for item in models.RetentionWorkflowType}
    aliases = {
        "inactive-members": models.RetentionWorkflowType.inactive_member_alert.value,
        "overdue-renewals": models.RetentionWorkflowType.renewal_reminder.value,
        "renewal-reminders": models.RetentionWorkflowType.renewal_reminder.value,
        "pending-approvals": models.RetentionWorkflowType.pending_trainer_approval.value,
        "trainer-follow-ups": models.RetentionWorkflowType.trainer_follow_up_reminder.value,
        "stalled-progress": models.RetentionWorkflowType.stalled_progress_alert.value,
        "high-risk-churn": models.RetentionWorkflowType.high_churn_risk.value,
    }
    normalized_type = aliases.get(workflow_type, workflow_type)
    if normalized_type not in allowed_types:
        raise HTTPException(status_code=422, detail="Unsupported action workflow type")
    membership = require_org_membership(db, organization_id, account, COACH_ROLES)
    trainer_scope = account.id if membership.role in {models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value} else None
    result = RetentionAutomationService(db).daily_actions(organization_id, persist=persist, trainer_account_id=trainer_scope)
    actions = [action for action in result["actions"] if action["workflow_type"] == normalized_type]
    return {"organization_id": organization_id, "actions": actions, "summary": {normalized_type: len(actions)}}


@router.post("/members/{member_id}/body-metrics", response_model=schemas.BodyMetricSnapshotOut)
def record_body_metrics(
    organization_id: int,
    member_id: int,
    payload: schemas.BodyMetricSnapshotCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.BodyMetricSnapshot:
    member = get_org_member(db, organization_id, member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    if member.account_id == account.id and account.id != member.assigned_trainer_id:
        recorded_by = None
    else:
        recorded_by = account.id
    snapshot = models.BodyMetricSnapshot(
        organization_id=organization_id,
        member_id=member.id,
        recorded_by_account_id=recorded_by,
        **payload.model_dump(),
    )
    db.add(snapshot)
    write_audit(db, "body_metrics.recorded", "body_metric_snapshot", None, account, organization_id, {"member_id": member.id})
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.post("/members/{member_id}/transformation-milestones", response_model=schemas.TransformationMilestoneOut)
def record_transformation_milestone(
    organization_id: int,
    member_id: int,
    payload: schemas.TransformationMilestoneCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.TransformationMilestone:
    member = get_org_member(db, organization_id, member_id, account, COACH_ROLES)
    milestone = models.TransformationMilestone(
        organization_id=organization_id,
        member_id=member.id,
        trainer_account_id=member.assigned_trainer_id,
        **payload.model_dump(),
    )
    db.add(milestone)
    write_audit(db, "transformation_milestone.recorded", "transformation_milestone", None, account, organization_id, {"member_id": member.id})
    db.commit()
    db.refresh(milestone)
    return milestone


@router.get("/members/{member_id}/transformation", response_model=schemas.TransformationSummaryOut)
def member_transformation_summary(
    organization_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    get_org_member(db, organization_id, member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    summary = TransformationService(db).member_summary(organization_id, member_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Member transformation summary not found")
    return summary


@router.get("/trainers/{trainer_account_id}/transformation", response_model=schemas.TrainerTransformationOut)
def trainer_transformation_success(
    organization_id: int,
    trainer_account_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    membership = require_org_membership(db, organization_id, account, COACH_ROLES)
    if membership.role in {models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value} and trainer_account_id != account.id:
        raise HTTPException(status_code=403, detail="Trainer can only view their own transformation metrics")
    return TransformationService(db).trainer_success(organization_id, trainer_account_id)


@router.get("/transformations/gym", response_model=schemas.GymTransformationOut)
def gym_transformation_metrics(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    return TransformationService(db).gym_metrics(organization_id)
