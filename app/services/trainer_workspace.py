from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models
from app.services.analytics import AnalyticsService


class TrainerWorkspaceService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService(db)

    def assigned_clients(self, organization_id: int, trainer_account_id: int) -> list[dict]:
        members = (
            self.db.query(models.UserProfile)
            .filter(
                models.UserProfile.organization_id == organization_id,
                models.UserProfile.assigned_trainer_id == trainer_account_id,
                models.UserProfile.status.in_([models.MemberStatus.active.value, models.MemberStatus.frozen.value]),
            )
            .order_by(models.UserProfile.name)
            .all()
        )
        return [self.analytics.member_summary(member) for member in members]

    def pending_plan_approvals(self, organization_id: int, trainer_account_id: int) -> list[dict]:
        plans = (
            self.db.query(models.WorkoutPlan)
            .join(models.UserProfile, models.UserProfile.id == models.WorkoutPlan.user_id)
            .filter(
                models.WorkoutPlan.organization_id == organization_id,
                models.UserProfile.assigned_trainer_id == trainer_account_id,
                models.WorkoutPlan.status.in_(
                    [
                        models.PlanReviewStatus.ai_generated.value,
                        models.PlanReviewStatus.pending_trainer_review.value,
                    ]
                ),
            )
            .order_by(desc(models.WorkoutPlan.created_at), desc(models.WorkoutPlan.id))
            .all()
        )
        return [
            {
                "plan_id": plan.id,
                "member": self.analytics.member_mini(plan.user),
                "title": plan.title,
                "week_start": plan.week_start,
                "status": plan.status,
                "created_at": plan.created_at,
                "rationale": plan.rationale,
            }
            for plan in plans
        ]

    def at_risk_clients(self, organization_id: int, trainer_account_id: int) -> list[dict]:
        return [client for client in self.assigned_clients(organization_id, trainer_account_id) if client["risk_signals"]]

    def client_progress_summary(self, organization_id: int, trainer_account_id: int, member_id: int) -> dict:
        member = (
            self.db.query(models.UserProfile)
            .filter(
                models.UserProfile.id == member_id,
                models.UserProfile.organization_id == organization_id,
                models.UserProfile.assigned_trainer_id == trainer_account_id,
            )
            .first()
        )
        if not member:
            return {}
        summary = self.analytics.member_summary(member)
        summary["analytics"] = self.analytics.member_analytics(member)
        return summary
