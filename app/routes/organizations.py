import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import get_settings
from app.db import get_db
from app.services.auth import create_invite_token, hash_invite_token, require_account
from app.services.explainability import ExplainabilityService
from app.services.notifications import NotificationService
from app.services.tenancy import ADMIN_ROLES, COACH_ROLES, OWNER_ROLES, get_org_member, normalize_slug, require_org_membership, require_plan_reviewer, serialize_goal, write_audit
from app.services.workout_planner import WorkoutPlanner


router = APIRouter(prefix="/organizations", tags=["organizations"])


def serialize_member_request(request: models.MemberRequest) -> dict:
    return {
        "id": request.id,
        "organization_id": request.organization_id,
        "member": {
            "id": request.member.id,
            "account_id": request.member.account_id,
            "organization_id": request.member.organization_id,
            "assigned_trainer_id": request.member.assigned_trainer_id,
            "member_code": request.member.member_code,
            "phone": request.member.phone,
            "email": request.member.email,
            "status": request.member.status,
            "name": request.member.name,
            "age": request.member.age,
            "fitness_goal": request.member.fitness_goal,
            "gym_type": request.member.gym_type,
            "joined_on": request.member.joined_on,
        },
        "request_type": request.request_type,
        "status": request.status,
        "title": request.title,
        "message": request.message,
        "payload": json.loads(request.payload_json or "{}"),
        "resolution_note": request.resolution_note,
        "created_by_account_id": request.created_by_account_id,
        "reviewed_by_account_id": request.reviewed_by_account_id,
        "reviewed_at": request.reviewed_at,
        "created_at": request.created_at,
    }


@router.post("", response_model=schemas.OrganizationOut)
def create_organization(
    payload: schemas.OrganizationCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.Organization:
    slug = normalize_slug(payload.slug)
    if db.query(models.Organization).filter(models.Organization.slug == slug).first():
        raise HTTPException(status_code=409, detail="Organization slug already exists")
    organization = models.Organization(**payload.model_dump(exclude={"slug"}), slug=slug)
    db.add(organization)
    db.flush()
    db.add(
        models.OrganizationMembership(
            organization_id=organization.id,
            account_id=account.id,
            role=models.OrganizationRole.gym_owner.value,
        )
    )
    write_audit(db, "organization.created", "organization", organization.id, account, organization.id)
    db.commit()
    db.refresh(organization)
    return organization


@router.get("", response_model=list[schemas.OrganizationOut])
def list_organizations(
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[models.Organization]:
    return (
        db.query(models.Organization)
        .join(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.account_id == account.id,
            models.OrganizationMembership.active.is_(True),
            models.Organization.status == models.OrganizationStatus.active.value,
        )
        .order_by(models.Organization.name)
        .all()
    )


@router.get("/{organization_id}")
def get_organization(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    membership = require_org_membership(db, organization_id, account)
    organization = db.get(models.Organization, organization_id)
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    active_members = (
        db.query(func.count(models.UserProfile.id))
        .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.status == models.MemberStatus.active.value)
        .scalar()
    )
    overdue_payments = (
        db.query(func.count(models.Payment.id))
        .filter(models.Payment.organization_id == organization_id, models.Payment.status == models.PaymentStatus.overdue.value)
        .scalar()
    )
    return {
        "organization": schemas.OrganizationOut.model_validate(organization).model_dump(),
        "role": membership.role,
        "summary": {
            "active_members": active_members,
            "overdue_payments": overdue_payments,
        },
    }


@router.post("/{organization_id}/staff", response_model=schemas.OrganizationMembershipOut)
def add_staff_membership(
    organization_id: int,
    payload: schemas.OrganizationMembershipCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.OrganizationMembership:
    require_org_membership(db, organization_id, account, OWNER_ROLES)
    if payload.role not in {role.value for role in models.OrganizationRole}:
        raise HTTPException(status_code=422, detail="Unsupported organization role")
    staff_account = db.get(models.Account, payload.account_id)
    if not staff_account:
        raise HTTPException(status_code=404, detail="Account not found")
    membership = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.account_id == payload.account_id,
        )
        .first()
    )
    if membership:
        membership.role = payload.role
        membership.active = True
    else:
        membership = models.OrganizationMembership(
            organization_id=organization_id,
            account_id=payload.account_id,
            role=payload.role,
        )
        db.add(membership)
    write_audit(db, "organization.staff_upserted", "account", payload.account_id, account, organization_id, {"role": payload.role})
    db.commit()
    db.refresh(membership)
    return membership


@router.get("/{organization_id}/members", response_model=list[schemas.UserProfileOut])
def list_members(
    organization_id: int,
    status: str | None = None,
    trainer_id: int | None = None,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[models.UserProfile]:
    membership = require_org_membership(db, organization_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    query = db.query(models.UserProfile).filter(models.UserProfile.organization_id == organization_id)
    if membership.role == models.OrganizationRole.trainer.value:
        query = query.filter(models.UserProfile.assigned_trainer_id == account.id)
    if membership.role == models.OrganizationRole.member.value:
        query = query.filter(models.UserProfile.account_id == account.id)
    if status:
        query = query.filter(models.UserProfile.status == status)
    if trainer_id:
        query = query.filter(models.UserProfile.assigned_trainer_id == trainer_id)
    return query.order_by(models.UserProfile.name).all()


@router.post("/{organization_id}/members", response_model=schemas.UserProfileOut)
def create_member(
    organization_id: int,
    payload: schemas.OrganizationMemberCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.UserProfile:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    if payload.assigned_trainer_id:
        trainer = db.get(models.Account, payload.assigned_trainer_id)
        if not trainer:
            raise HTTPException(status_code=404, detail="Trainer account not found")
        require_org_membership(db, organization_id, trainer, COACH_ROLES)
    values = payload.model_dump()
    member = models.UserProfile(
        organization_id=organization_id,
        joined_on=values.pop("joined_on") or date.today(),
        status=values.pop("status"),
        account_id=values.pop("account_id"),
        **values,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    generated_plan = WorkoutPlanner(db).generate_week(member)
    if member.assigned_trainer_id and generated_plan.status == models.PlanReviewStatus.pending_trainer_review.value:
        NotificationService(db).emit(
            models.NotificationEventType.ai_plan_pending_review.value,
            "AI plan pending review",
            f"{member.name}'s generated workout plan needs trainer review.",
            organization_id=organization_id,
            recipient_account_id=member.assigned_trainer_id,
            entity_type="workout_plan",
            entity_id=generated_plan.id,
            payload={"member_id": member.id},
        )
    write_audit(db, "member.created", "user_profile", member.id, account, organization_id)
    db.commit()
    return member


@router.get("/{organization_id}/members/{member_id}/detail")
def member_detail(
    organization_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    member = get_org_member(db, organization_id, member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    latest_membership = (
        db.query(models.MemberMembership)
        .filter(models.MemberMembership.organization_id == organization_id, models.MemberMembership.member_id == member.id)
        .order_by(desc(models.MemberMembership.ends_on), desc(models.MemberMembership.id))
        .first()
    )
    payments = (
        db.query(models.Payment)
        .filter(models.Payment.organization_id == organization_id, models.Payment.member_id == member.id)
        .order_by(desc(models.Payment.due_on), desc(models.Payment.id))
        .limit(10)
        .all()
    )
    checkins = (
        db.query(models.AttendanceCheckin)
        .filter(models.AttendanceCheckin.organization_id == organization_id, models.AttendanceCheckin.member_id == member.id)
        .order_by(desc(models.AttendanceCheckin.checked_in_at), desc(models.AttendanceCheckin.id))
        .limit(10)
        .all()
    )
    workflows = (
        db.query(models.RetentionWorkflow)
        .filter(models.RetentionWorkflow.organization_id == organization_id, models.RetentionWorkflow.member_id == member.id)
        .order_by(desc(models.RetentionWorkflow.created_at), desc(models.RetentionWorkflow.id))
        .limit(10)
        .all()
    )
    requests = (
        db.query(models.MemberRequest)
        .filter(models.MemberRequest.organization_id == organization_id, models.MemberRequest.member_id == member.id)
        .order_by(desc(models.MemberRequest.created_at), desc(models.MemberRequest.id))
        .limit(10)
        .all()
    )
    return {
        "member": schemas.UserProfileOut.model_validate(member).model_dump(),
        "login_status": "active" if member.account_id else "invited" if member.invited_at else "not_invited",
        "latest_membership": schemas.MemberMembershipOut.model_validate(latest_membership).model_dump() if latest_membership else None,
        "payments": [schemas.PaymentOut.model_validate(payment).model_dump() for payment in payments],
        "attendance": [schemas.AttendanceCheckinOut.model_validate(checkin).model_dump() for checkin in checkins],
        "workflows": [
            {
                "id": workflow.id,
                "workflow_type": workflow.workflow_type,
                "status": workflow.status,
                "priority": workflow.priority,
                "title": workflow.title,
                "message": workflow.message,
                "due_on": workflow.due_on,
                "metadata": workflow.metadata_json,
            }
            for workflow in workflows
        ],
        "requests": [serialize_member_request(request) for request in requests],
    }


@router.post("/{organization_id}/members/{member_id}/invite", response_model=schemas.MemberInviteOut)
def invite_member(
    organization_id: int,
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    member = get_org_member(db, organization_id, member_id, account, ADMIN_ROLES)
    if member.account_id:
        raise HTTPException(status_code=409, detail="Member already has a login account")
    token = create_invite_token()
    member.invite_token_hash = hash_invite_token(token)
    member.invited_at = datetime.utcnow()
    settings = get_settings()
    frontend_url = _invite_frontend_url(settings, request)
    invite_url = f"{frontend_url.rstrip('/')}/app/invite/{token}"
    channels = [models.NotificationChannel.in_app.value]
    if member.phone:
        channels.append(models.NotificationChannel.whatsapp.value)
    NotificationService(db).emit(
        models.NotificationEventType.trainer_follow_up_due.value,
        "Member invite prepared",
        f"Invite {member.name} to activate their FitGen.ai member account: {invite_url}",
        organization_id=organization_id,
        recipient_account_id=account.id,
        recipient_user_id=member.id,
        entity_type="user_profile",
        entity_id=member.id,
        payload={"invite_url": invite_url, "member_id": member.id, "phone_present": bool(member.phone)},
        channels=channels,
    )
    write_audit(db, "member.invited", "user_profile", member.id, account, organization_id, {"channel": "whatsapp" if member.phone else "manual"})
    db.commit()
    return {
        "member_id": member.id,
        "invite_url": invite_url,
        "status": "prepared",
        "channel": "whatsapp" if member.phone else "manual",
    }


def _invite_frontend_url(settings, request: Request) -> str:
    if settings.frontend_app_url:
        return settings.frontend_app_url.rstrip("/")
    request_origin = str(request.base_url).rstrip("/")
    for origin in settings.cors_origins:
        normalized = origin.rstrip("/")
        if "localhost" in normalized or "127.0.0.1" in normalized:
            continue
        if normalized != request_origin:
            return normalized
    return request_origin


@router.patch("/{organization_id}/members/{member_id}/trainer", response_model=schemas.UserProfileOut)
def assign_trainer(
    organization_id: int,
    member_id: int,
    trainer_account_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.UserProfile:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    trainer = db.get(models.Account, trainer_account_id)
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer account not found")
    require_org_membership(db, organization_id, trainer, COACH_ROLES)
    member = get_org_member(db, organization_id, member_id, account, ADMIN_ROLES)
    member.assigned_trainer_id = trainer_account_id
    write_audit(db, "member.trainer_assigned", "user_profile", member.id, account, organization_id, {"trainer_account_id": trainer_account_id})
    db.commit()
    db.refresh(member)
    return member


@router.get("/{organization_id}/membership-plans", response_model=list[schemas.MembershipPlanOut])
def list_membership_plans(
    organization_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[models.MembershipPlan]:
    require_org_membership(db, organization_id, account, COACH_ROLES)
    return (
        db.query(models.MembershipPlan)
        .filter(models.MembershipPlan.organization_id == organization_id, models.MembershipPlan.active.is_(True))
        .order_by(models.MembershipPlan.duration_days, models.MembershipPlan.price_amount)
        .all()
    )


@router.post("/{organization_id}/membership-plans", response_model=schemas.MembershipPlanOut)
def create_membership_plan(
    organization_id: int,
    payload: schemas.MembershipPlanCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.MembershipPlan:
    require_org_membership(db, organization_id, account, ADMIN_ROLES)
    plan = models.MembershipPlan(organization_id=organization_id, **payload.model_dump())
    db.add(plan)
    write_audit(db, "membership_plan.created", "membership_plan", None, account, organization_id)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/{organization_id}/members/{member_id}/memberships", response_model=schemas.MemberMembershipOut)
def create_member_membership(
    organization_id: int,
    member_id: int,
    payload: schemas.MemberMembershipCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.MemberMembership:
    get_org_member(db, organization_id, member_id, account, ADMIN_ROLES)
    if payload.plan_id:
        plan = db.get(models.MembershipPlan, payload.plan_id)
        if not plan or plan.organization_id != organization_id:
            raise HTTPException(status_code=400, detail="Membership plan does not belong to organization")
    membership = models.MemberMembership(organization_id=organization_id, member_id=member_id, **payload.model_dump())
    db.add(membership)
    write_audit(db, "member_membership.created", "member_membership", None, account, organization_id)
    db.commit()
    db.refresh(membership)
    return membership


@router.post("/{organization_id}/members/{member_id}/payments", response_model=schemas.PaymentOut)
def record_payment(
    organization_id: int,
    member_id: int,
    payload: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.Payment:
    get_org_member(db, organization_id, member_id, account, ADMIN_ROLES)
    if payload.membership_id:
        membership = db.get(models.MemberMembership, payload.membership_id)
        if not membership or membership.organization_id != organization_id or membership.member_id != member_id:
            raise HTTPException(status_code=400, detail="Membership does not belong to member")
    payment = models.Payment(organization_id=organization_id, member_id=member_id, **payload.model_dump())
    db.add(payment)
    write_audit(db, "payment.recorded", "payment", None, account, organization_id, {"status": payload.status})
    if payload.status == models.PaymentStatus.paid.value:
        member = db.get(models.UserProfile, member_id)
        if member and member.account_id:
            NotificationService(db).emit(
                models.NotificationEventType.payment_received.value,
                "Payment received",
                f"Payment of {payload.currency} {payload.amount:.2f} has been recorded.",
                organization_id=organization_id,
                recipient_account_id=member.account_id,
                recipient_user_id=member.id,
                entity_type="payment",
                entity_id=None,
                payload={"amount": payload.amount, "currency": payload.currency},
            )
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/{organization_id}/members/{member_id}/attendance", response_model=schemas.AttendanceCheckinOut)
def record_attendance(
    organization_id: int,
    member_id: int,
    payload: schemas.AttendanceCheckinCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> models.AttendanceCheckin:
    get_org_member(db, organization_id, member_id, account, COACH_ROLES)
    checkin = models.AttendanceCheckin(
        organization_id=organization_id,
        member_id=member_id,
        method=payload.method,
        notes=payload.notes,
        recorded_by_account_id=account.id,
    )
    db.add(checkin)
    write_audit(db, "attendance.recorded", "attendance_checkin", None, account, organization_id)
    db.commit()
    db.refresh(checkin)
    return checkin


@router.post("/{organization_id}/attendance/import", response_model=schemas.AttendanceImportResult)
def import_attendance(
    organization_id: int,
    rows: list[schemas.AttendanceImportRow],
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, COACH_ROLES)
    created = 0
    skipped = 0
    errors: list[str] = []
    allowed_methods = {method.value for method in models.AttendanceMethod}
    for index, row in enumerate(rows, start=1):
        if row.method not in allowed_methods:
            skipped += 1
            errors.append(f"Row {index}: unsupported attendance method {row.method}")
            continue
        member = None
        if row.member_id is not None:
            member = db.get(models.UserProfile, row.member_id)
            if member and member.organization_id != organization_id:
                member = None
        elif row.member_code:
            member = (
                db.query(models.UserProfile)
                .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.member_code == row.member_code)
                .first()
            )
        if member is None:
            skipped += 1
            errors.append(f"Row {index}: member not found")
            continue
        checkin = models.AttendanceCheckin(
            organization_id=organization_id,
            member_id=member.id,
            checked_in_at=row.checked_in_at or datetime.utcnow(),
            method=row.method,
            notes=row.notes,
            recorded_by_account_id=account.id,
        )
        db.add(checkin)
        created += 1
    write_audit(db, "attendance.imported", "attendance_checkin", None, account, organization_id, {"created": created, "skipped": skipped})
    db.commit()
    return {"created": created, "skipped": skipped, "errors": errors[:25]}


@router.get("/{organization_id}/member-requests", response_model=list[schemas.MemberRequestOut])
def list_member_requests(
    organization_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    membership = require_org_membership(db, organization_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    query = db.query(models.MemberRequest).filter(models.MemberRequest.organization_id == organization_id)
    if membership.role == models.OrganizationRole.member.value:
        member = (
            db.query(models.UserProfile)
            .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.account_id == account.id)
            .first()
        )
        if member is None:
            return []
        query = query.filter(models.MemberRequest.member_id == member.id)
    elif membership.role in {models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value}:
        query = query.join(models.UserProfile, models.UserProfile.id == models.MemberRequest.member_id).filter(models.UserProfile.assigned_trainer_id == account.id)
    if status:
        query = query.filter(models.MemberRequest.status == status)
    requests = query.order_by(desc(models.MemberRequest.created_at), desc(models.MemberRequest.id)).limit(100).all()
    return [serialize_member_request(request) for request in requests]


@router.post("/{organization_id}/members/{member_id}/requests", response_model=schemas.MemberRequestOut)
def create_member_request(
    organization_id: int,
    member_id: int,
    payload: schemas.MemberRequestCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    member = get_org_member(db, organization_id, member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    request = models.MemberRequest(
        organization_id=organization_id,
        member_id=member.id,
        request_type=payload.request_type,
        title=payload.title,
        message=payload.message,
        payload_json=json.dumps(payload.payload, sort_keys=True),
        created_by_account_id=account.id,
    )
    db.add(request)
    db.flush()
    assignee_id = member.assigned_trainer_id or _default_owner_id(db, organization_id)
    workflow = models.RetentionWorkflow(
        organization_id=organization_id,
        member_id=member.id,
        assigned_account_id=assignee_id,
        workflow_type=models.RetentionWorkflowType.trainer_follow_up_reminder.value,
        status=models.RetentionWorkflowStatus.open.value,
        priority="high" if payload.request_type == models.MemberRequestType.injury_report.value else "medium",
        title=f"Member request: {payload.title}",
        message=f"{member.name} submitted a {payload.request_type.replace('_', ' ')} request.",
        due_on=date.today(),
        source_entity_type="member_request",
        source_entity_id=request.id,
        metadata_json=json.dumps({"member_request_id": request.id, "request_type": payload.request_type}, sort_keys=True),
    )
    db.add(workflow)
    write_audit(db, "member_request.created", "member_request", request.id, account, organization_id, {"request_type": payload.request_type})
    db.commit()
    db.refresh(request)
    return serialize_member_request(request)


@router.patch("/{organization_id}/member-requests/{request_id}", response_model=schemas.MemberRequestOut)
def update_member_request(
    organization_id: int,
    request_id: int,
    payload: schemas.MemberRequestUpdate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, COACH_ROLES)
    request = db.get(models.MemberRequest, request_id)
    if not request or request.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Member request not found")
    request.status = payload.status
    request.resolution_note = payload.resolution_note
    request.reviewed_by_account_id = account.id
    request.reviewed_at = datetime.utcnow()
    write_audit(db, "member_request.updated", "member_request", request.id, account, organization_id, {"status": payload.status})
    db.commit()
    db.refresh(request)
    return serialize_member_request(request)


def _default_owner_id(db: Session, organization_id: int) -> int | None:
    membership = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.active.is_(True),
            models.OrganizationMembership.role.in_([models.OrganizationRole.gym_owner.value, models.OrganizationRole.admin.value]),
        )
        .order_by(models.OrganizationMembership.id)
        .first()
    )
    return membership.account_id if membership else None


@router.post("/{organization_id}/members/{member_id}/goals", response_model=schemas.GoalOut)
def create_goal(
    organization_id: int,
    member_id: int,
    payload: schemas.GoalCreate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    member = get_org_member(db, organization_id, member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    goal = models.Goal(
        organization_id=organization_id,
        member_id=member.id,
        created_by_account_id=account.id,
        assigned_trainer_id=payload.assigned_trainer_id or member.assigned_trainer_id,
        **payload.model_dump(exclude={"assigned_trainer_id"}),
    )
    db.add(goal)
    write_audit(db, "goal.created", "goal", None, account, organization_id)
    db.commit()
    db.refresh(goal)
    return serialize_goal(goal)


@router.get("/{organization_id}/members/{member_id}/goals", response_model=list[schemas.GoalOut])
def list_goals(
    organization_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    get_org_member(db, organization_id, member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    goals = (
        db.query(models.Goal)
        .filter(models.Goal.organization_id == organization_id, models.Goal.member_id == member_id)
        .order_by(desc(models.Goal.created_at))
        .all()
    )
    return [serialize_goal(goal) for goal in goals]


@router.patch("/{organization_id}/goals/{goal_id}", response_model=schemas.GoalOut)
def update_goal_progress(
    organization_id: int,
    goal_id: int,
    payload: schemas.GoalProgressUpdate,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    require_org_membership(db, organization_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    goal = db.get(models.Goal, goal_id)
    if not goal or goal.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Goal not found")
    get_org_member(db, organization_id, goal.member_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    if payload.current_value is not None:
        goal.current_value = payload.current_value
    if payload.status is not None:
        if payload.status not in {status.value for status in models.GoalStatus}:
            raise HTTPException(status_code=422, detail="Unsupported goal status")
        goal.status = payload.status
        if payload.status == models.GoalStatus.achieved.value:
            goal.achieved_at = datetime.utcnow()
    write_audit(db, "goal.updated", "goal", goal.id, account, organization_id, payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(goal)
    return serialize_goal(goal)


@router.post("/{organization_id}/workout-plans/{plan_id}/review")
def review_workout_plan(
    organization_id: int,
    plan_id: int,
    payload: schemas.WorkoutPlanReview,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> dict:
    plan = db.get(models.WorkoutPlan, plan_id)
    if not plan or plan.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    require_plan_reviewer(db, plan, account)
    get_org_member(db, organization_id, plan.user_id, account, COACH_ROLES)
    plan.status = payload.status
    plan.trainer_notes = payload.trainer_notes
    plan.reviewed_by_account_id = account.id
    plan.reviewed_at = datetime.utcnow()
    write_audit(db, "workout_plan.reviewed", "workout_plan", plan.id, account, organization_id, {"status": payload.status})
    if plan.user.account_id and payload.status == models.PlanReviewStatus.trainer_approved.value:
        NotificationService(db).emit(
            models.NotificationEventType.plan_approved.value,
            "Workout plan approved",
            f"Your trainer approved {plan.title}.",
            organization_id=organization_id,
            recipient_account_id=plan.user.account_id,
            recipient_user_id=plan.user_id,
            entity_type="workout_plan",
            entity_id=plan.id,
            payload={"status": payload.status},
        )
    db.commit()
    db.refresh(plan)
    return {"workout_plan": WorkoutPlanner(db).serialize_plan(plan)}


@router.get("/{organization_id}/workout-plans/{plan_id}/explainability", response_model=list[schemas.AIExplainabilityOut])
def workout_plan_explainability(
    organization_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    account: models.Account = Depends(require_account),
) -> list[dict]:
    plan = db.get(models.WorkoutPlan, plan_id)
    if not plan or plan.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Workout plan not found")
    get_org_member(db, organization_id, plan.user_id, account, COACH_ROLES | {models.OrganizationRole.member.value})
    service = ExplainabilityService(db)
    records = (
        db.query(models.AIExplainabilityRecord)
        .filter(
            models.AIExplainabilityRecord.organization_id == organization_id,
            models.AIExplainabilityRecord.workout_plan_id == plan_id,
        )
        .order_by(models.AIExplainabilityRecord.created_at)
        .all()
    )
    return [service.serialize(record) for record in records]
