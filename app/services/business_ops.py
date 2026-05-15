from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.services.analytics import AnalyticsService
from app.services.notifications import NotificationService
from app.services.tenancy import serialize_goal


def _month_key(value: date | datetime | None) -> str:
    if value is None:
        return "unknown"
    return f"{value.year:04d}-{value.month:02d}"


class RetentionIntelligenceService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService(db)

    def member_renewal_risk(self, member: models.UserProfile) -> dict[str, Any]:
        membership = self._latest_membership(member)
        adherence = self.analytics.adherence(member)
        signals: list[dict[str, Any]] = []
        today = date.today()

        current_attendance = self._attendance_count(member.organization_id, member.id, today - timedelta(days=30), today)
        previous_attendance = self._attendance_count(member.organization_id, member.id, today - timedelta(days=60), today - timedelta(days=31))
        if previous_attendance >= 4 and current_attendance < previous_attendance * 0.6:
            signals.append(
                {
                    "code": "declining_attendance",
                    "severity": "high",
                    "message": "Attendance has dropped by more than 40% compared with the previous 30 days.",
                    "contribution": 22,
                }
            )
        if current_attendance == 0:
            signals.append(
                {
                    "code": "no_recent_attendance",
                    "severity": "high",
                    "message": "No gym check-ins in the last 30 days.",
                    "contribution": 24,
                }
            )
        if adherence["missed_sessions"] >= 2:
            signals.append(
                {
                    "code": "missed_workouts",
                    "severity": "medium",
                    "message": "Two or more planned sessions are missed in the current plan.",
                    "contribution": 14,
                }
            )
        if adherence["last_workout_on"] is None or adherence["last_workout_on"] < today - timedelta(days=10):
            signals.append(
                {
                    "code": "inactivity",
                    "severity": "high",
                    "message": "No completed workout in the last 10 days.",
                    "contribution": 20,
                }
            )
        if adherence["planned_sessions"] > 0 and adherence["adherence_rate"] < 0.6:
            signals.append(
                {
                    "code": "declining_adherence",
                    "severity": "medium",
                    "message": "Current plan adherence is below 60%.",
                    "contribution": 16,
                }
            )
        stagnant_goals = self._stagnant_goals(member)
        if stagnant_goals:
            signals.append(
                {
                    "code": "goal_stagnation",
                    "severity": "medium",
                    "message": f"{len(stagnant_goals)} active goal(s) have not moved recently.",
                    "contribution": 12,
                }
            )
        if membership and (membership.status == models.MembershipStatus.expired.value or membership.ends_on < today):
            signals.append(
                {
                    "code": "expired_membership",
                    "severity": "critical",
                    "message": "Membership is expired.",
                    "contribution": 30,
                }
            )
        elif membership and membership.ends_on <= today + timedelta(days=14):
            signals.append(
                {
                    "code": "renewal_window",
                    "severity": "medium",
                    "message": "Membership expires within 14 days.",
                    "contribution": 10,
                }
            )
        if self._lacks_trainer_engagement(member):
            signals.append(
                {
                    "code": "lack_of_trainer_engagement",
                    "severity": "medium",
                    "message": "No recent trainer review or assigned trainer engagement is visible.",
                    "contribution": 12,
                }
            )

        score = min(100.0, round(sum(signal["contribution"] for signal in signals), 1))
        level = self._risk_level(score)
        revenue_at_risk = self._membership_revenue(membership) if level in {"high", "critical"} else 0
        return {
            "member": self.analytics.member_mini(member),
            "membership": self.analytics.membership_summary(member),
            "score": score,
            "level": level,
            "signals": signals,
            "forecast_renewal_on": membership.ends_on if membership else None,
            "revenue_at_risk": revenue_at_risk,
            "generated_at": datetime.utcnow(),
        }

    def snapshot_member_risk(self, member: models.UserProfile) -> dict[str, Any]:
        risk = self.member_renewal_risk(member)
        membership = self._latest_membership(member)
        snapshot = models.RenewalRiskSnapshot(
            organization_id=member.organization_id,
            member_id=member.id,
            membership_id=membership.id if membership else None,
            score=risk["score"],
            level=risk["level"],
            signals_json=json.dumps(risk["signals"], sort_keys=True),
            forecast_renewal_on=risk["forecast_renewal_on"],
            revenue_at_risk=risk["revenue_at_risk"],
        )
        self.db.add(snapshot)
        return risk

    def at_risk_renewals(self, organization_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
        members = self._org_members(organization_id)
        risks = [self.member_renewal_risk(member) for member in members]
        risky = [risk for risk in risks if risk["level"] in {"high", "critical"}]
        return sorted(risky, key=lambda item: item["score"], reverse=True)[:limit]

    def renewal_forecast(self, organization_id: int, *, window_days: int = 30) -> dict[str, Any]:
        today = date.today()
        memberships = (
            self.db.query(models.MemberMembership)
            .filter(
                models.MemberMembership.organization_id == organization_id,
                models.MemberMembership.ends_on >= today,
                models.MemberMembership.ends_on <= today + timedelta(days=window_days),
                models.MemberMembership.status == models.MembershipStatus.active.value,
            )
            .all()
        )
        risks = [self.member_renewal_risk(membership.member) for membership in memberships]
        high_risk = [risk for risk in risks if risk["level"] in {"high", "critical"}]
        forecast_revenue = sum(self._membership_revenue(membership) for membership in memberships)
        revenue_at_risk = sum(risk["revenue_at_risk"] for risk in high_risk)
        expected_renewals = sum(1 for risk in risks if risk["level"] in {"low", "medium"})
        return {
            "organization_id": organization_id,
            "window_days": window_days,
            "expiring_memberships": len(memberships),
            "high_risk_renewals": len(high_risk),
            "forecast_revenue": round(forecast_revenue, 2),
            "revenue_at_risk": round(revenue_at_risk, 2),
            "expected_renewals": expected_renewals,
            "renewal_probability": round(expected_renewals / len(memberships), 3) if memberships else 0,
            "at_risk_members": sorted(high_risk, key=lambda item: item["score"], reverse=True),
        }

    def _org_members(self, organization_id: int) -> list[models.UserProfile]:
        return (
            self.db.query(models.UserProfile)
            .filter(models.UserProfile.organization_id == organization_id)
            .order_by(models.UserProfile.name)
            .all()
        )

    def _latest_membership(self, member: models.UserProfile) -> models.MemberMembership | None:
        return (
            self.db.query(models.MemberMembership)
            .filter(models.MemberMembership.organization_id == member.organization_id, models.MemberMembership.member_id == member.id)
            .order_by(desc(models.MemberMembership.ends_on), desc(models.MemberMembership.id))
            .first()
        )

    def _membership_revenue(self, membership: models.MemberMembership | None) -> float:
        if not membership or not membership.plan:
            return 0
        return round(float(membership.plan.price_amount), 2)

    def _attendance_count(self, organization_id: int | None, member_id: int, start: date, end: date) -> int:
        if organization_id is None:
            return 0
        return (
            self.db.query(func.count(models.AttendanceCheckin.id))
            .filter(
                models.AttendanceCheckin.organization_id == organization_id,
                models.AttendanceCheckin.member_id == member_id,
                models.AttendanceCheckin.checked_in_at >= datetime.combine(start, datetime.min.time()),
                models.AttendanceCheckin.checked_in_at <= datetime.combine(end, datetime.max.time()),
            )
            .scalar()
            or 0
        )

    def _stagnant_goals(self, member: models.UserProfile) -> list[models.Goal]:
        stale_before = datetime.utcnow() - timedelta(days=30)
        goals = (
            self.db.query(models.Goal)
            .filter(
                models.Goal.organization_id == member.organization_id,
                models.Goal.member_id == member.id,
                models.Goal.status == models.GoalStatus.active.value,
            )
            .all()
        )
        return [goal for goal in goals if goal.updated_at < stale_before and (goal.current_value or 0) < (goal.target_value or 1)]

    def _lacks_trainer_engagement(self, member: models.UserProfile) -> bool:
        if member.assigned_trainer_id is None:
            return True
        recent_review = (
            self.db.query(models.WorkoutPlan)
            .filter(
                models.WorkoutPlan.organization_id == member.organization_id,
                models.WorkoutPlan.user_id == member.id,
                models.WorkoutPlan.reviewed_by_account_id == member.assigned_trainer_id,
                models.WorkoutPlan.reviewed_at >= datetime.utcnow() - timedelta(days=21),
            )
            .first()
        )
        return recent_review is None

    def _risk_level(self, score: float) -> str:
        if score >= 70:
            return models.RenewalRiskLevel.critical.value
        if score >= 45:
            return models.RenewalRiskLevel.high.value
        if score >= 20:
            return models.RenewalRiskLevel.medium.value
        return models.RenewalRiskLevel.low.value


class RevenueOperationsService:
    def __init__(self, db: Session):
        self.db = db
        self.retention = RetentionIntelligenceService(db)
        self.analytics = AnalyticsService(db)

    def dashboard(self, organization_id: int) -> dict[str, Any]:
        active_memberships = self._active_memberships(organization_id)
        unpaid_members = self.unpaid_members(organization_id)
        overdue_revenue = sum(item["amount_due"] for item in unpaid_members)
        risk_summary = Counter(risk["level"] for risk in [self.retention.member_renewal_risk(member) for member in self._members(organization_id)])
        return {
            "organization_id": organization_id,
            "monthly_recurring_revenue": round(sum(self._monthly_value(membership) for membership in active_memberships), 2),
            "active_memberships": len(active_memberships),
            "expiring_memberships_30d": self._expiring_membership_count(organization_id, 30),
            "unpaid_members": unpaid_members,
            "overdue_revenue": round(overdue_revenue, 2),
            "renewal_trends": self.renewal_trends(organization_id),
            "retention_trends": self.retention_trends(organization_id),
            "churn_risk_summary": {level: risk_summary.get(level, 0) for level in ["low", "medium", "high", "critical"]},
        }

    def unpaid_members(self, organization_id: int) -> list[dict[str, Any]]:
        rows = (
            self.db.query(models.Payment.member_id, func.coalesce(func.sum(models.Payment.amount), 0.0), func.min(models.Payment.due_on), func.count(models.Payment.id))
            .filter(
                models.Payment.organization_id == organization_id,
                models.Payment.status.in_([models.PaymentStatus.pending.value, models.PaymentStatus.overdue.value, models.PaymentStatus.failed.value]),
            )
            .group_by(models.Payment.member_id)
            .all()
        )
        items = []
        for member_id, amount_due, oldest_due_on, overdue_payments in rows:
            member = self.db.get(models.UserProfile, member_id)
            if member:
                items.append(
                    {
                        "member": self.analytics.member_mini(member),
                        "amount_due": round(float(amount_due or 0), 2),
                        "oldest_due_on": oldest_due_on,
                        "overdue_payments": overdue_payments,
                    }
                )
        return sorted(items, key=lambda item: (item["oldest_due_on"] or date.max, -item["amount_due"]))

    def renewal_trends(self, organization_id: int, months: int = 6) -> list[dict[str, Any]]:
        since = datetime.utcnow() - timedelta(days=31 * months)
        renewals = (
            self.db.query(models.MemberMembership)
            .filter(
                models.MemberMembership.organization_id == organization_id,
                models.MemberMembership.renewal_of_id.isnot(None),
                models.MemberMembership.created_at >= since,
            )
            .all()
        )
        by_month: dict[str, dict[str, Any]] = self._empty_trend(months)
        for membership in renewals:
            key = _month_key(membership.created_at)
            if key in by_month:
                by_month[key]["renewals"] += 1
                by_month[key]["revenue"] += float(membership.plan.price_amount if membership.plan else 0)
        return list(by_month.values())

    def retention_trends(self, organization_id: int, months: int = 6) -> list[dict[str, Any]]:
        since = date.today() - timedelta(days=31 * months)
        expired = (
            self.db.query(models.MemberMembership)
            .filter(models.MemberMembership.organization_id == organization_id, models.MemberMembership.ends_on >= since)
            .all()
        )
        by_month: dict[str, dict[str, Any]] = self._empty_trend(months)
        renewed_source_ids = {
            row[0]
            for row in self.db.query(models.MemberMembership.renewal_of_id)
            .filter(models.MemberMembership.organization_id == organization_id, models.MemberMembership.renewal_of_id.isnot(None))
            .all()
        }
        for membership in expired:
            key = _month_key(membership.ends_on)
            if key in by_month:
                by_month[key]["expired"] += 1
                if membership.id not in renewed_source_ids and membership.ends_on < date.today():
                    by_month[key]["churned"] += 1
        return list(by_month.values())

    def _active_memberships(self, organization_id: int) -> list[models.MemberMembership]:
        return (
            self.db.query(models.MemberMembership)
            .filter(
                models.MemberMembership.organization_id == organization_id,
                models.MemberMembership.status == models.MembershipStatus.active.value,
                models.MemberMembership.ends_on >= date.today(),
            )
            .all()
        )

    def _members(self, organization_id: int) -> list[models.UserProfile]:
        return self.db.query(models.UserProfile).filter(models.UserProfile.organization_id == organization_id).all()

    def _monthly_value(self, membership: models.MemberMembership) -> float:
        if not membership.plan or membership.plan.duration_days <= 0:
            return 0
        return float(membership.plan.price_amount) / membership.plan.duration_days * 30

    def _expiring_membership_count(self, organization_id: int, days: int) -> int:
        today = date.today()
        return (
            self.db.query(func.count(models.MemberMembership.id))
            .filter(
                models.MemberMembership.organization_id == organization_id,
                models.MemberMembership.status == models.MembershipStatus.active.value,
                models.MemberMembership.ends_on >= today,
                models.MemberMembership.ends_on <= today + timedelta(days=days),
            )
            .scalar()
            or 0
        )

    def _empty_trend(self, months: int) -> dict[str, dict[str, Any]]:
        today = date.today().replace(day=1)
        buckets = {}
        for offset in range(months - 1, -1, -1):
            month = today.month - offset
            year = today.year
            while month <= 0:
                month += 12
                year -= 1
            key = f"{year:04d}-{month:02d}"
            buckets[key] = {"period": key, "revenue": 0, "renewals": 0, "expired": 0, "churned": 0}
        return buckets


class TrainerPerformanceService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService(db)
        self.retention = RetentionIntelligenceService(db)

    def comparison(self, organization_id: int) -> dict[str, Any]:
        trainer_ids = self._trainer_ids(organization_id)
        return {"organization_id": organization_id, "trainers": [self.trainer_performance(organization_id, trainer_id) for trainer_id in trainer_ids]}

    def trainer_performance(self, organization_id: int, trainer_account_id: int) -> dict[str, Any]:
        trainer = self.db.get(models.Account, trainer_account_id)
        members = (
            self.db.query(models.UserProfile)
            .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.assigned_trainer_id == trainer_account_id)
            .all()
        )
        summaries = [self.analytics.member_summary(member) for member in members]
        risks = [self.retention.member_renewal_risk(member) for member in members]
        active_members = [member for member in members if member.status == models.MemberStatus.active.value]
        retained = [member for member in members if self._has_active_or_renewed_membership(organization_id, member.id)]
        adherence_rates = [summary["adherence"]["adherence_rate"] for summary in summaries]
        return {
            "trainer_account_id": trainer_account_id,
            "trainer_email": trainer.email if trainer else None,
            "active_client_count": len(active_members),
            "client_retention_rate": round(len(retained) / len(members), 3) if members else 0,
            "avg_client_adherence": round(mean(adherence_rates), 3) if adherence_rates else 0,
            "goal_success_rate": self._goal_success_rate(organization_id, trainer_account_id),
            "consistency_trend": self._consistency_trend(members),
            "overdue_approvals": self._overdue_approvals(organization_id, trainer_account_id),
            "inactive_clients": sum(1 for summary in summaries if any(signal["code"] == "inactivity" for signal in summary["risk_signals"])),
            "high_risk_clients": sum(1 for risk in risks if risk["level"] in {"high", "critical"}),
        }

    def _trainer_ids(self, organization_id: int) -> list[int]:
        membership_ids = [
            row[0]
            for row in self.db.query(models.OrganizationMembership.account_id)
            .filter(
                models.OrganizationMembership.organization_id == organization_id,
                models.OrganizationMembership.active.is_(True),
                models.OrganizationMembership.role.in_([models.OrganizationRole.trainer.value, models.OrganizationRole.nutritionist.value]),
            )
            .all()
        ]
        assigned_ids = [
            row[0]
            for row in self.db.query(models.UserProfile.assigned_trainer_id)
            .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.assigned_trainer_id.isnot(None))
            .distinct()
            .all()
        ]
        return sorted(set(membership_ids + assigned_ids))

    def _has_active_or_renewed_membership(self, organization_id: int, member_id: int) -> bool:
        return (
            self.db.query(models.MemberMembership)
            .filter(
                models.MemberMembership.organization_id == organization_id,
                models.MemberMembership.member_id == member_id,
                models.MemberMembership.status == models.MembershipStatus.active.value,
                models.MemberMembership.ends_on >= date.today(),
            )
            .first()
            is not None
        )

    def _goal_success_rate(self, organization_id: int, trainer_account_id: int) -> float:
        goals = (
            self.db.query(models.Goal)
            .filter(models.Goal.organization_id == organization_id, models.Goal.assigned_trainer_id == trainer_account_id)
            .all()
        )
        if not goals:
            return 0
        achieved = sum(1 for goal in goals if goal.status == models.GoalStatus.achieved.value)
        return round(achieved / len(goals), 3)

    def _consistency_trend(self, members: list[models.UserProfile]) -> float:
        if not members:
            return 0
        trends = []
        for member in members:
            current = self._completed_workout_days(member.id, date.today() - timedelta(days=30), date.today())
            previous = self._completed_workout_days(member.id, date.today() - timedelta(days=60), date.today() - timedelta(days=31))
            trends.append(current - previous)
        return round(mean(trends), 2) if trends else 0

    def _completed_workout_days(self, member_id: int, start: date, end: date) -> int:
        rows = (
            self.db.query(models.WorkoutLog.performed_on)
            .filter(models.WorkoutLog.user_id == member_id, models.WorkoutLog.performed_on >= start, models.WorkoutLog.performed_on <= end, models.WorkoutLog.completed.is_(True))
            .distinct()
            .all()
        )
        return len(rows)

    def _overdue_approvals(self, organization_id: int, trainer_account_id: int) -> int:
        return (
            self.db.query(func.count(models.WorkoutPlan.id))
            .join(models.UserProfile, models.UserProfile.id == models.WorkoutPlan.user_id)
            .filter(
                models.WorkoutPlan.organization_id == organization_id,
                models.UserProfile.assigned_trainer_id == trainer_account_id,
                models.WorkoutPlan.status.in_([models.PlanReviewStatus.ai_generated.value, models.PlanReviewStatus.pending_trainer_review.value]),
                models.WorkoutPlan.created_at < datetime.utcnow() - timedelta(days=2),
            )
            .scalar()
            or 0
        )


class RetentionAutomationService:
    RENEWAL_FUNNEL_DAYS = {15, 7, 3}

    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService(db)
        self.retention = RetentionIntelligenceService(db)
        self.settings = get_settings()

    def daily_actions(self, organization_id: int, *, persist: bool = False, trainer_account_id: int | None = None) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []
        member_query = self.db.query(models.UserProfile).filter(models.UserProfile.organization_id == organization_id)
        if trainer_account_id is not None:
            member_query = member_query.filter(models.UserProfile.assigned_trainer_id == trainer_account_id)
        members = member_query.all()
        for member in members:
            risk = self.retention.member_renewal_risk(member)
            actions.extend(self._actions_for_member(member, risk))
        approvals = self._pending_approval_actions(organization_id, trainer_account_id=trainer_account_id)
        actions.extend(approvals)
        if persist:
            actions = [self._upsert_workflow(action) for action in actions]
        summary = Counter(action["workflow_type"] for action in actions)
        return {"organization_id": organization_id, "actions": sorted(actions, key=lambda item: (item["priority"] != "high", item["due_on"] or date.max)), "summary": dict(summary)}

    def _actions_for_member(self, member: models.UserProfile, risk: dict[str, Any]) -> list[dict[str, Any]]:
        actions = []
        codes = {signal["code"] for signal in risk["signals"]}
        member_mini = self.analytics.member_mini(member)

        silent_dropout_action = self._silent_dropout_action(member, member_mini)
        if silent_dropout_action:
            actions.append(silent_dropout_action)
        elif "inactivity" in codes or "no_recent_attendance" in codes:
            actions.append(
                self._action(
                    member,
                    member_mini,
                    models.RetentionWorkflowType.inactive_member_alert.value,
                    "high",
                    "Inactive member follow-up",
                    f"{member.name} has recent inactivity and needs a retention touchpoint.",
                    date.today(),
                    {"risk_score": risk["score"]},
                )
            )

        renewal_funnel_action = self._renewal_funnel_action(member, member_mini, risk)
        if "expired_membership" in codes:
            actions.append(
                self._action(
                    member,
                    member_mini,
                    models.RetentionWorkflowType.renewal_reminder.value,
                    "high",
                    "Renewal conversation due",
                    f"{member.name} is in the renewal window. Confirm plan, payment, and next coaching step.",
                    date.today(),
                    {"risk_score": risk["score"], "forecast_renewal_on": str(risk["forecast_renewal_on"])},
                )
            )
        elif renewal_funnel_action:
            actions.append(renewal_funnel_action)
        elif "renewal_window" in codes:
            actions.append(
                self._action(
                    member,
                    member_mini,
                    models.RetentionWorkflowType.renewal_reminder.value,
                    "medium",
                    "Renewal conversation due",
                    f"{member.name} is in the renewal window. Confirm plan, payment, and next coaching step.",
                    date.today(),
                    {"risk_score": risk["score"], "forecast_renewal_on": str(risk["forecast_renewal_on"])},
                )
            )
        if "goal_stagnation" in codes:
            actions.append(
                self._action(
                    member,
                    member_mini,
                    models.RetentionWorkflowType.stalled_progress_alert.value,
                    "medium",
                    "Progress has stalled",
                    f"{member.name} has active goals without recent progress movement.",
                    date.today() + timedelta(days=1),
                    {"risk_score": risk["score"]},
                )
            )
        if "lack_of_trainer_engagement" in codes:
            actions.append(
                self._action(
                    member,
                    member_mini,
                    models.RetentionWorkflowType.trainer_follow_up_reminder.value,
                    "medium",
                    "Trainer follow-up needed",
                    f"{member.name} needs recent trainer engagement documented.",
                    date.today() + timedelta(days=1),
                    {"risk_score": risk["score"]},
                )
            )
        if risk["level"] in {"high", "critical"}:
            actions.append(
                self._action(
                    member,
                    member_mini,
                    models.RetentionWorkflowType.high_churn_risk.value,
                    "high",
                    "High churn-risk client",
                    f"{member.name} has a {risk['level']} renewal risk score.",
                    date.today(),
                    {"risk_score": risk["score"], "level": risk["level"]},
                )
            )
        return actions

    def _silent_dropout_action(self, member: models.UserProfile, member_mini: dict[str, Any]) -> dict[str, Any] | None:
        if member.status != models.MemberStatus.active.value or member.organization_id is None:
            return None
        today = date.today()
        last_access = self._last_access_checkin(member)
        baseline = member.joined_on or member.created_at.date()
        last_seen_on = last_access.checked_in_at.date() if last_access else None
        absent_since = last_seen_on or baseline
        absent_days = (today - absent_since).days
        if absent_days < 7:
            return None
        contact_status = "ready" if member.phone else "member_phone_missing"
        metadata = {
            "automation": "silent_dropout",
            "market": "IN",
            "absent_days": absent_days,
            "last_access_on": str(last_seen_on) if last_seen_on else None,
            "access_methods": [models.AttendanceMethod.qr.value, models.AttendanceMethod.biometric.value],
            "recommended_channels": [models.NotificationChannel.whatsapp.value, models.NotificationChannel.in_app.value],
            "whatsapp_template": "silent_dropout_nudge_v1",
            "contact_status": contact_status,
            "recipient_phone_present": bool(member.phone),
            "booking_link": self._booking_link(member),
        }
        return self._action(
            member,
            member_mini,
            models.RetentionWorkflowType.inactive_member_alert.value,
            "high",
            "Silent dropout alarm",
            f"{member.name} has no QR or biometric access scan for {absent_days} days. Send a WhatsApp nudge or call today.",
            today,
            metadata,
            source_entity_type="attendance_gap",
            source_entity_id=member.id,
        )

    def _renewal_funnel_action(self, member: models.UserProfile, member_mini: dict[str, Any], risk: dict[str, Any]) -> dict[str, Any] | None:
        membership = self._latest_active_membership(member)
        if membership is None:
            return None
        today = date.today()
        days_remaining = (membership.ends_on - today).days
        if days_remaining not in self.RENEWAL_FUNNEL_DAYS:
            return None
        amount = float(membership.plan.price_amount) if membership.plan else 0.0
        payment_link = self._payment_link(member, membership)
        payment_link_status = "ready" if payment_link else "provider_not_configured"
        metadata = {
            "automation": "renewal_funnel",
            "market": "IN",
            "days_to_expiry": days_remaining,
            "membership_id": membership.id,
            "plan_id": membership.plan_id,
            "plan_name": membership.plan.name if membership.plan else None,
            "amount": amount,
            "currency": membership.plan.currency if membership.plan else "INR",
            "payment_methods": ["upi", "card", "netbanking"],
            "payment_link": payment_link,
            "payment_link_status": payment_link_status,
            "recommended_channels": [models.NotificationChannel.whatsapp.value, models.NotificationChannel.in_app.value],
            "whatsapp_template": f"renewal_{days_remaining}_day_payment_link_v1",
            "contact_status": "ready" if member.phone else "member_phone_missing",
            "risk_score": risk["score"],
        }
        priority = "high" if days_remaining == 3 else "medium"
        return self._action(
            member,
            member_mini,
            models.RetentionWorkflowType.renewal_reminder.value,
            priority,
            f"Renewal funnel: {days_remaining}-day payment link",
            f"{member.name}'s membership expires in {days_remaining} days. Send the renewal payment link over WhatsApp and confirm UPI/card/netbanking payment.",
            today,
            metadata,
            source_entity_type="member_membership",
            source_entity_id=membership.id,
        )

    def _last_access_checkin(self, member: models.UserProfile) -> models.AttendanceCheckin | None:
        return (
            self.db.query(models.AttendanceCheckin)
            .filter(
                models.AttendanceCheckin.organization_id == member.organization_id,
                models.AttendanceCheckin.member_id == member.id,
                models.AttendanceCheckin.method.in_([models.AttendanceMethod.qr.value, models.AttendanceMethod.biometric.value]),
            )
            .order_by(desc(models.AttendanceCheckin.checked_in_at), desc(models.AttendanceCheckin.id))
            .first()
        )

    def _latest_active_membership(self, member: models.UserProfile) -> models.MemberMembership | None:
        return (
            self.db.query(models.MemberMembership)
            .filter(
                models.MemberMembership.organization_id == member.organization_id,
                models.MemberMembership.member_id == member.id,
                models.MemberMembership.status == models.MembershipStatus.active.value,
                models.MemberMembership.ends_on >= date.today(),
            )
            .order_by(desc(models.MemberMembership.ends_on), desc(models.MemberMembership.id))
            .first()
        )

    def _pending_approval_actions(self, organization_id: int, *, trainer_account_id: int | None = None) -> list[dict[str, Any]]:
        query = self.db.query(models.WorkoutPlan).join(models.UserProfile, models.UserProfile.id == models.WorkoutPlan.user_id).filter(
            models.WorkoutPlan.organization_id == organization_id,
            models.WorkoutPlan.status.in_([models.PlanReviewStatus.ai_generated.value, models.PlanReviewStatus.pending_trainer_review.value]),
        )
        if trainer_account_id is not None:
            query = query.filter(models.UserProfile.assigned_trainer_id == trainer_account_id)
        plans = query.all()
        return [
            self._action(
                plan.user,
                self.analytics.member_mini(plan.user),
                models.RetentionWorkflowType.pending_trainer_approval.value,
                "high" if plan.created_at < datetime.utcnow() - timedelta(days=2) else "medium",
                "Plan approval pending",
                f"{plan.user.name}'s AI-generated plan is waiting for trainer review.",
                date.today(),
                {"plan_id": plan.id},
                source_entity_type="workout_plan",
                source_entity_id=plan.id,
            )
            for plan in plans
        ]

    def _action(
        self,
        member: models.UserProfile,
        member_mini: dict[str, Any],
        workflow_type: str,
        priority: str,
        title: str,
        message: str,
        due_on: date,
        metadata: dict[str, Any],
        *,
        source_entity_type: str = "member",
        source_entity_id: int | None = None,
    ) -> dict[str, Any]:
        return {
            "id": None,
            "organization_id": member.organization_id,
            "member": member_mini,
            "assigned_account_id": member.assigned_trainer_id or self._default_assignee_id(member.organization_id),
            "workflow_type": workflow_type,
            "status": models.RetentionWorkflowStatus.open.value,
            "priority": priority,
            "title": title,
            "message": message,
            "due_on": due_on,
            "source_entity_type": source_entity_type,
            "source_entity_id": source_entity_id or member.id,
            "metadata": metadata,
            "created_at": None,
        }

    def _upsert_workflow(self, action: dict[str, Any]) -> dict[str, Any]:
        existing = (
            self.db.query(models.RetentionWorkflow)
            .filter(
                models.RetentionWorkflow.organization_id == action["organization_id"],
                models.RetentionWorkflow.member_id == action["member"]["id"],
                models.RetentionWorkflow.workflow_type == action["workflow_type"],
                models.RetentionWorkflow.status == models.RetentionWorkflowStatus.open.value,
            )
            .first()
        )
        if existing:
            workflow = existing
            workflow.priority = action["priority"]
            workflow.message = action["message"]
            workflow.due_on = action["due_on"]
            workflow.source_entity_type = action["source_entity_type"]
            workflow.source_entity_id = action["source_entity_id"]
            workflow.metadata_json = json.dumps(action["metadata"], sort_keys=True)
        else:
            workflow = models.RetentionWorkflow(
                organization_id=action["organization_id"],
                member_id=action["member"]["id"],
                assigned_account_id=action["assigned_account_id"],
                workflow_type=action["workflow_type"],
                status=action["status"],
                priority=action["priority"],
                title=action["title"],
                message=action["message"],
                due_on=action["due_on"],
                source_entity_type=action["source_entity_type"],
                source_entity_id=action["source_entity_id"],
                metadata_json=json.dumps(action["metadata"], sort_keys=True),
            )
            self.db.add(workflow)
            self.db.flush()
            self._emit_notification(workflow)
        return self._serialize_workflow(workflow)

    def _emit_notification(self, workflow: models.RetentionWorkflow) -> None:
        event_type = {
            models.RetentionWorkflowType.inactive_member_alert.value: models.NotificationEventType.inactive_member.value,
            models.RetentionWorkflowType.trainer_follow_up_reminder.value: models.NotificationEventType.trainer_follow_up_due.value,
            models.RetentionWorkflowType.pending_trainer_approval.value: models.NotificationEventType.ai_plan_pending_review.value,
            models.RetentionWorkflowType.renewal_reminder.value: models.NotificationEventType.membership_expiring.value,
            models.RetentionWorkflowType.stalled_progress_alert.value: models.NotificationEventType.stalled_progress.value,
            models.RetentionWorkflowType.high_churn_risk.value: models.NotificationEventType.renewal_risk_detected.value,
        }.get(workflow.workflow_type, models.NotificationEventType.trainer_follow_up_due.value)
        metadata = json.loads(workflow.metadata_json or "{}")
        requested_channels = set(metadata.get("recommended_channels") or [])
        channels: list[str] = []
        if workflow.assigned_account_id is not None:
            channels.append(models.NotificationChannel.in_app.value)
        if models.NotificationChannel.whatsapp.value in requested_channels:
            channels.append(models.NotificationChannel.whatsapp.value)
        if not channels:
            return
        NotificationService(self.db).emit(
            event_type,
            workflow.title,
            workflow.message,
            organization_id=workflow.organization_id,
            recipient_account_id=workflow.assigned_account_id,
            recipient_user_id=workflow.member_id,
            entity_type="retention_workflow",
            entity_id=workflow.id,
            payload={"workflow_type": workflow.workflow_type, "priority": workflow.priority, **metadata},
            channels=channels,
        )

    def _default_assignee_id(self, organization_id: int | None) -> int | None:
        if organization_id is None:
            return None
        membership = (
            self.db.query(models.OrganizationMembership)
            .filter(
                models.OrganizationMembership.organization_id == organization_id,
                models.OrganizationMembership.active.is_(True),
                models.OrganizationMembership.role.in_([models.OrganizationRole.gym_owner.value, models.OrganizationRole.admin.value]),
            )
            .order_by(models.OrganizationMembership.role.desc(), models.OrganizationMembership.id)
            .first()
        )
        return membership.account_id if membership else None

    def _booking_link(self, member: models.UserProfile) -> str | None:
        if not self.settings.booking_base_url:
            return None
        return f"{self.settings.booking_base_url.rstrip('/')}/organizations/{member.organization_id}/members/{member.id}"

    def _payment_link(self, member: models.UserProfile, membership: models.MemberMembership) -> str | None:
        if not self.settings.payment_links_enabled or not self.settings.payment_link_base_url:
            return None
        return f"{self.settings.payment_link_base_url.rstrip('/')}/organizations/{member.organization_id}/members/{member.id}/memberships/{membership.id}"

    def _serialize_workflow(self, workflow: models.RetentionWorkflow) -> dict[str, Any]:
        return {
            "id": workflow.id,
            "organization_id": workflow.organization_id,
            "member": self.analytics.member_mini(workflow.member),
            "assigned_account_id": workflow.assigned_account_id,
            "workflow_type": workflow.workflow_type,
            "status": workflow.status,
            "priority": workflow.priority,
            "title": workflow.title,
            "message": workflow.message,
            "due_on": workflow.due_on,
            "source_entity_type": workflow.source_entity_type,
            "source_entity_id": workflow.source_entity_id,
            "metadata": json.loads(workflow.metadata_json or "{}"),
            "created_at": workflow.created_at,
        }


class TransformationService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService(db)

    def member_summary(self, organization_id: int, member_id: int) -> dict[str, Any]:
        member = (
            self.db.query(models.UserProfile)
            .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.id == member_id)
            .first()
        )
        if member is None:
            return {}
        return {
            "member": self.analytics.member_mini(member),
            "body_metric_improvements": self.body_metric_improvements(organization_id, member_id),
            "strength_progression": self.analytics.volume_progression(member_id),
            "consistency_improvement": self.consistency_improvement(member_id),
            "goal_completion_history": [serialize_goal(goal) for goal in self._goals(organization_id, member_id)],
            "milestones": self._milestones(organization_id, member_id),
        }

    def trainer_success(self, organization_id: int, trainer_account_id: int) -> dict[str, Any]:
        members = (
            self.db.query(models.UserProfile)
            .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.assigned_trainer_id == trainer_account_id)
            .all()
        )
        improvements = [self.body_metric_improvements(organization_id, member.id) for member in members]
        consistency = [self.consistency_improvement(member.id) for member in members]
        return {
            "trainer_account_id": trainer_account_id,
            "active_clients": sum(1 for member in members if member.status == models.MemberStatus.active.value),
            "clients_with_improvements": sum(1 for item in improvements if any(value is not None and value > 0 for value in item.values())),
            "avg_consistency_improvement": round(mean(consistency), 2) if consistency else 0,
            "goal_success_rate": self._goal_success_rate(organization_id, trainer_account_id),
            "milestones_90d": self._milestone_count(organization_id, trainer_account_id=trainer_account_id),
        }

    def gym_metrics(self, organization_id: int) -> dict[str, Any]:
        members = self.db.query(models.UserProfile).filter(models.UserProfile.organization_id == organization_id).all()
        consistency = [self.consistency_improvement(member.id) for member in members]
        body_improved = sum(
            1
            for member in members
            if any(value is not None and value > 0 for value in self.body_metric_improvements(organization_id, member.id).values())
        )
        trainer_ids = sorted({member.assigned_trainer_id for member in members if member.assigned_trainer_id is not None})
        return {
            "organization_id": organization_id,
            "members_tracked": len(members),
            "members_with_body_improvements": body_improved,
            "avg_consistency_improvement": round(mean(consistency), 2) if consistency else 0,
            "goal_completion_pct": self.analytics.goal_completion_pct(organization_id),
            "milestones_90d": self._milestone_count(organization_id),
            "trainer_success": [self.trainer_success(organization_id, trainer_id) for trainer_id in trainer_ids],
        }

    def body_metric_improvements(self, organization_id: int, member_id: int) -> dict[str, float | None]:
        snapshots = (
            self.db.query(models.BodyMetricSnapshot)
            .filter(models.BodyMetricSnapshot.organization_id == organization_id, models.BodyMetricSnapshot.member_id == member_id)
            .order_by(models.BodyMetricSnapshot.measured_on, models.BodyMetricSnapshot.id)
            .all()
        )
        if len(snapshots) < 2:
            return {"weight_kg": None, "body_fat_pct": None, "waist_cm": None, "chest_cm": None, "hip_cm": None}
        first = snapshots[0]
        latest = snapshots[-1]
        return {
            "weight_kg": self._delta(first.weight_kg, latest.weight_kg, lower_is_better=True),
            "body_fat_pct": self._delta(first.body_fat_pct, latest.body_fat_pct, lower_is_better=True),
            "waist_cm": self._delta(first.waist_cm, latest.waist_cm, lower_is_better=True),
            "chest_cm": self._delta(first.chest_cm, latest.chest_cm),
            "hip_cm": self._delta(first.hip_cm, latest.hip_cm),
        }

    def consistency_improvement(self, member_id: int) -> float:
        current = self._completed_workout_days(member_id, date.today() - timedelta(days=30), date.today())
        previous = self._completed_workout_days(member_id, date.today() - timedelta(days=60), date.today() - timedelta(days=31))
        return round(current - previous, 2)

    def _delta(self, first: float | None, latest: float | None, *, lower_is_better: bool = False) -> float | None:
        if first is None or latest is None:
            return None
        value = first - latest if lower_is_better else latest - first
        return round(value, 2)

    def _goals(self, organization_id: int, member_id: int) -> list[models.Goal]:
        return (
            self.db.query(models.Goal)
            .filter(models.Goal.organization_id == organization_id, models.Goal.member_id == member_id)
            .order_by(desc(models.Goal.updated_at), desc(models.Goal.id))
            .all()
        )

    def _milestones(self, organization_id: int, member_id: int) -> list[models.TransformationMilestone]:
        return (
            self.db.query(models.TransformationMilestone)
            .filter(models.TransformationMilestone.organization_id == organization_id, models.TransformationMilestone.member_id == member_id)
            .order_by(desc(models.TransformationMilestone.achieved_on), desc(models.TransformationMilestone.id))
            .all()
        )

    def _completed_workout_days(self, member_id: int, start: date, end: date) -> int:
        rows = (
            self.db.query(models.WorkoutLog.performed_on)
            .filter(models.WorkoutLog.user_id == member_id, models.WorkoutLog.performed_on >= start, models.WorkoutLog.performed_on <= end, models.WorkoutLog.completed.is_(True))
            .distinct()
            .all()
        )
        return len(rows)

    def _goal_success_rate(self, organization_id: int, trainer_account_id: int) -> float:
        goals = (
            self.db.query(models.Goal)
            .filter(models.Goal.organization_id == organization_id, models.Goal.assigned_trainer_id == trainer_account_id)
            .all()
        )
        if not goals:
            return 0
        return round(sum(1 for goal in goals if goal.status == models.GoalStatus.achieved.value) / len(goals), 3)

    def _milestone_count(self, organization_id: int, trainer_account_id: int | None = None) -> int:
        query = self.db.query(func.count(models.TransformationMilestone.id)).filter(
            models.TransformationMilestone.organization_id == organization_id,
            models.TransformationMilestone.achieved_on >= date.today() - timedelta(days=90),
        )
        if trainer_account_id is not None:
            query = query.filter(models.TransformationMilestone.trainer_account_id == trainer_account_id)
        return query.scalar() or 0


class BusinessDashboardService:
    def __init__(self, db: Session):
        self.db = db
        self.revenue = RevenueOperationsService(db)
        self.retention = RetentionIntelligenceService(db)
        self.trainers = TrainerPerformanceService(db)
        self.automation = RetentionAutomationService(db)

    def owner_dashboard(self, organization_id: int) -> dict[str, Any]:
        return {
            "organization_id": organization_id,
            "revenue": self.revenue.dashboard(organization_id),
            "renewal_forecast": self.retention.renewal_forecast(organization_id, window_days=30),
            "trainer_performance": self.trainers.comparison(organization_id)["trainers"],
            "daily_actions": self.automation.daily_actions(organization_id),
            "at_risk_members": self.retention.at_risk_renewals(organization_id, limit=25),
        }
