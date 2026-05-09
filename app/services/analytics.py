from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.services.tenancy import serialize_goal


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def member_summary(self, member: models.UserProfile) -> dict[str, Any]:
        goals = self.active_goals(member.organization_id, member.id)
        adherence = self.adherence(member)
        readiness = self.readiness(member)
        membership = self.membership_summary(member)
        latest_workout = self.latest_workout(member)
        risk_signals = self.risk_signals(member, adherence, readiness, goals)
        return {
            "member": self.member_mini(member),
            "active_goals": [serialize_goal(goal) for goal in goals],
            "adherence": adherence,
            "latest_workout": latest_workout,
            "readiness": readiness,
            "membership": membership,
            "risk_signals": risk_signals,
        }

    def member_analytics(self, member: models.UserProfile) -> dict[str, Any]:
        return {
            "member_id": member.id,
            "workout_consistency": self.adherence(member),
            "attendance_rate": self.attendance_rate(member.organization_id, member.id),
            "goal_completion_pct": self.goal_completion_pct(member.organization_id, member.id),
            "volume_progression": self.volume_progression(member.id),
            "readiness": self.readiness(member),
        }

    def trainer_analytics(self, organization_id: int, trainer_account_id: int) -> dict[str, Any]:
        members = (
            self.db.query(models.UserProfile)
            .filter(
                models.UserProfile.organization_id == organization_id,
                models.UserProfile.assigned_trainer_id == trainer_account_id,
            )
            .all()
        )
        summaries = [self.member_summary(member) for member in members]
        adherence_rates = [item["adherence"]["adherence_rate"] for item in summaries]
        overdue_goals = (
            self.db.query(func.count(models.Goal.id))
            .filter(
                models.Goal.organization_id == organization_id,
                models.Goal.assigned_trainer_id == trainer_account_id,
                models.Goal.status == models.GoalStatus.active.value,
                models.Goal.target_date.isnot(None),
                models.Goal.target_date < date.today(),
            )
            .scalar()
            or 0
        )
        pending_reviews = (
            self.db.query(func.count(models.WorkoutPlan.id))
            .join(models.UserProfile, models.UserProfile.id == models.WorkoutPlan.user_id)
            .filter(
                models.WorkoutPlan.organization_id == organization_id,
                models.UserProfile.assigned_trainer_id == trainer_account_id,
                models.WorkoutPlan.status == models.PlanReviewStatus.pending_trainer_review.value,
            )
            .scalar()
            or 0
        )
        return {
            "trainer_account_id": trainer_account_id,
            "assigned_clients": len(members),
            "at_risk_clients": sum(1 for item in summaries if item["risk_signals"]),
            "pending_plan_reviews": pending_reviews,
            "average_adherence_rate": round(mean(adherence_rates), 3) if adherence_rates else 0,
            "overdue_goals": overdue_goals,
        }

    def gym_analytics(self, organization_id: int) -> dict[str, Any]:
        month_start = date.today().replace(day=1)
        active_members = (
            self.db.query(func.count(models.UserProfile.id))
            .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.status == models.MemberStatus.active.value)
            .scalar()
            or 0
        )
        active_memberships = (
            self.db.query(func.count(models.MemberMembership.id))
            .filter(
                models.MemberMembership.organization_id == organization_id,
                models.MemberMembership.status == models.MembershipStatus.active.value,
                models.MemberMembership.ends_on >= date.today(),
            )
            .scalar()
            or 0
        )
        monthly_revenue = (
            self.db.query(func.coalesce(func.sum(models.Payment.amount), 0.0))
            .filter(
                models.Payment.organization_id == organization_id,
                models.Payment.status == models.PaymentStatus.paid.value,
                models.Payment.paid_on >= month_start,
            )
            .scalar()
            or 0
        )
        overdue_revenue = (
            self.db.query(func.coalesce(func.sum(models.Payment.amount), 0.0))
            .filter(models.Payment.organization_id == organization_id, models.Payment.status == models.PaymentStatus.overdue.value)
            .scalar()
            or 0
        )
        attendance_30d = (
            self.db.query(func.count(models.AttendanceCheckin.id))
            .filter(
                models.AttendanceCheckin.organization_id == organization_id,
                models.AttendanceCheckin.checked_in_at >= datetime.utcnow() - timedelta(days=30),
            )
            .scalar()
            or 0
        )
        renewals_30d = (
            self.db.query(func.count(models.MemberMembership.id))
            .filter(
                models.MemberMembership.organization_id == organization_id,
                models.MemberMembership.renewal_of_id.isnot(None),
                models.MemberMembership.created_at >= datetime.utcnow() - timedelta(days=30),
            )
            .scalar()
            or 0
        )
        trainer_ids = [
            row[0]
            for row in self.db.query(models.UserProfile.assigned_trainer_id)
            .filter(models.UserProfile.organization_id == organization_id, models.UserProfile.assigned_trainer_id.isnot(None))
            .distinct()
            .all()
        ]
        return {
            "organization_id": organization_id,
            "active_members": active_members,
            "active_memberships": active_memberships,
            "monthly_revenue": float(monthly_revenue),
            "overdue_revenue": float(overdue_revenue),
            "attendance_30d": attendance_30d,
            "goal_completion_pct": self.goal_completion_pct(organization_id),
            "membership_renewals_30d": renewals_30d,
            "trainer_performance": [self.trainer_analytics(organization_id, trainer_id) for trainer_id in trainer_ids],
        }

    def active_goals(self, organization_id: int | None, member_id: int) -> list[models.Goal]:
        query = self.db.query(models.Goal).filter(models.Goal.member_id == member_id, models.Goal.status == models.GoalStatus.active.value)
        if organization_id is not None:
            query = query.filter(models.Goal.organization_id == organization_id)
        return query.order_by(models.Goal.target_date.is_(None), models.Goal.target_date).all()

    def adherence(self, member: models.UserProfile) -> dict[str, Any]:
        since = date.today() - timedelta(days=30)
        logs = (
            self.db.query(models.WorkoutLog)
            .filter(models.WorkoutLog.user_id == member.id, models.WorkoutLog.performed_on >= since)
            .all()
        )
        completed_logs = [log for log in logs if log.completed]
        current_plan = (
            self.db.query(models.WorkoutPlan)
            .filter(models.WorkoutPlan.user_id == member.id)
            .order_by(models.WorkoutPlan.week_start.desc(), models.WorkoutPlan.id.desc())
            .first()
        )
        planned_sessions = len({exercise.day_index for exercise in current_plan.exercises}) if current_plan else 0
        completed_sessions = len({log.performed_on for log in completed_logs})
        missed_sessions = max(0, planned_sessions - completed_sessions)
        last_workout_on = max((log.performed_on for log in completed_logs), default=None)
        return {
            "planned_sessions": planned_sessions,
            "completed_sessions": completed_sessions,
            "missed_sessions": missed_sessions,
            "adherence_rate": round(completed_sessions / planned_sessions, 3) if planned_sessions else (1.0 if completed_sessions else 0.0),
            "workout_logs_30d": len(logs),
            "last_workout_on": last_workout_on,
        }

    def latest_workout(self, member: models.UserProfile) -> dict[str, Any]:
        session = (
            self.db.query(models.WorkoutSession)
            .filter(models.WorkoutSession.user_id == member.id)
            .order_by(models.WorkoutSession.started_at.desc(), models.WorkoutSession.id.desc())
            .first()
        )
        if session:
            return {
                "session_id": session.id,
                "workout_plan_id": session.workout_plan_id,
                "performed_on": session.planned_for or session.started_at.date(),
                "status": session.status,
                "completion_rate": session.completion_rate,
            }
        log = (
            self.db.query(models.WorkoutLog)
            .filter(models.WorkoutLog.user_id == member.id)
            .order_by(models.WorkoutLog.performed_on.desc(), models.WorkoutLog.id.desc())
            .first()
        )
        return {
            "session_id": None,
            "workout_plan_id": None,
            "performed_on": log.performed_on if log else None,
            "status": "logged" if log else None,
            "completion_rate": 1.0 if log and log.completed else None,
        }

    def readiness(self, member: models.UserProfile) -> dict[str, Any]:
        since = datetime.utcnow() - timedelta(days=14)
        checkins = (
            self.db.query(models.ReadinessCheckin)
            .filter(models.ReadinessCheckin.user_id == member.id, models.ReadinessCheckin.created_at >= since)
            .all()
        )

        def avg(attr: str) -> float | None:
            values = [getattr(item, attr) for item in checkins if getattr(item, attr) is not None]
            return round(mean(values), 2) if values else None

        average_energy = avg("energy")
        average_soreness = avg("soreness")
        average_stress = avg("stress")
        average_pain = avg("pain")
        high_fatigue = any(
            value is not None and value >= 8
            for value in [average_soreness, average_stress, average_pain]
        ) or (average_energy is not None and average_energy <= 3)
        return {
            "checkins_14d": len(checkins),
            "average_energy": average_energy,
            "average_soreness": average_soreness,
            "average_stress": average_stress,
            "average_pain": average_pain,
            "high_fatigue": high_fatigue,
        }

    def membership_summary(self, member: models.UserProfile) -> dict[str, Any]:
        membership = (
            self.db.query(models.MemberMembership)
            .filter(models.MemberMembership.member_id == member.id)
            .order_by(models.MemberMembership.ends_on.desc(), models.MemberMembership.id.desc())
            .first()
        )
        if not membership:
            return {"status": None, "plan_name": None, "ends_on": None, "days_remaining": None}
        return {
            "status": membership.status,
            "plan_name": membership.plan.name if membership.plan else None,
            "ends_on": membership.ends_on,
            "days_remaining": (membership.ends_on - date.today()).days,
        }

    def risk_signals(
        self,
        member: models.UserProfile,
        adherence: dict[str, Any],
        readiness: dict[str, Any],
        active_goals: list[models.Goal],
    ) -> list[dict[str, str]]:
        signals: list[dict[str, str]] = []
        if adherence["last_workout_on"] is None or adherence["last_workout_on"] < date.today() - timedelta(days=7):
            signals.append({"code": "inactivity", "severity": "high", "message": "No completed workout in the last 7 days."})
        if adherence["missed_sessions"] >= 2:
            signals.append({"code": "missed_workouts", "severity": "medium", "message": "Missed two or more planned sessions in the current plan."})
        if adherence["adherence_rate"] < 0.6 and adherence["planned_sessions"] > 0:
            signals.append({"code": "declining_adherence", "severity": "medium", "message": "Current adherence is below 60%."})
        if any(goal.target_date and goal.target_date < date.today() for goal in active_goals):
            signals.append({"code": "overdue_goals", "severity": "medium", "message": "One or more active goals are past target date."})
        if readiness["high_fatigue"]:
            signals.append({"code": "high_fatigue", "severity": "high", "message": "Recent readiness signals indicate elevated fatigue or pain."})
        return signals

    def attendance_rate(self, organization_id: int | None, member_id: int) -> float:
        if organization_id is None:
            return 0
        since = datetime.utcnow() - timedelta(days=30)
        checkins = (
            self.db.query(func.count(models.AttendanceCheckin.id))
            .filter(
                models.AttendanceCheckin.organization_id == organization_id,
                models.AttendanceCheckin.member_id == member_id,
                models.AttendanceCheckin.checked_in_at >= since,
            )
            .scalar()
            or 0
        )
        return round(min(checkins / 12, 1.0), 3)

    def goal_completion_pct(self, organization_id: int | None, member_id: int | None = None) -> float:
        query = self.db.query(models.Goal)
        if organization_id is not None:
            query = query.filter(models.Goal.organization_id == organization_id)
        if member_id is not None:
            query = query.filter(models.Goal.member_id == member_id)
        goals = query.all()
        if not goals:
            return 0
        achieved = sum(1 for goal in goals if goal.status == models.GoalStatus.achieved.value)
        return round((achieved / len(goals)) * 100, 1)

    def volume_progression(self, member_id: int) -> list[dict[str, Any]]:
        since = date.today() - timedelta(days=90)
        logs = (
            self.db.query(models.WorkoutLog)
            .filter(models.WorkoutLog.user_id == member_id, models.WorkoutLog.performed_on >= since)
            .order_by(models.WorkoutLog.performed_on)
            .all()
        )
        by_week: dict[str, float] = defaultdict(float)
        for log in logs:
            week_start = log.performed_on - timedelta(days=log.performed_on.weekday())
            by_week[week_start.isoformat()] += log.weight_kg * log.reps_completed
        return [{"week_start": week, "volume": round(volume, 2)} for week, volume in sorted(by_week.items())]

    def member_mini(self, member: models.UserProfile) -> dict[str, Any]:
        return {
            "id": member.id,
            "account_id": member.account_id,
            "organization_id": member.organization_id,
            "assigned_trainer_id": member.assigned_trainer_id,
            "member_code": member.member_code,
            "status": member.status,
            "name": member.name,
            "age": member.age,
            "fitness_goal": member.fitness_goal,
            "gym_type": member.gym_type,
            "joined_on": member.joined_on,
        }
