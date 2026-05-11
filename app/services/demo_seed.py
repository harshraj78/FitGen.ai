from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.services.auth import create_session, hash_password, normalize_email
from app.services.business_ops import RetentionAutomationService, RetentionIntelligenceService
from app.services.diet_planner import DietPlanner
from app.services.workout_planner import WorkoutPlanner


DEMO_PASSWORD = "fitgen-demo"


class DemoSeedService:
    def __init__(self, db: Session):
        self.db = db

    def seed_business_demo(self) -> dict:
        owner = self._account("owner@fitgen.demo")
        trainer = self._account("trainer@fitgen.demo")
        admin = self._account("admin@fitgen.demo")
        member_account = self._account("member@fitgen.demo")
        organization = self._organization()
        self._membership(organization, owner, models.OrganizationRole.gym_owner.value)
        self._membership(organization, trainer, models.OrganizationRole.trainer.value)
        self._membership(organization, admin, models.OrganizationRole.admin.value)

        monthly = self._plan(organization, "Monthly Coaching", 30, 3500)
        quarterly = self._plan(organization, "Quarterly Transformation", 90, 9000)
        annual = self._plan(organization, "Annual Performance", 365, 32000)

        members = [
            self._member(organization, "Aarav Mehta", "FG-1001", trainer, member_account, 82, "fat_loss", "active"),
            self._member(organization, "Nisha Rao", "FG-1002", trainer, None, 61, "muscle_gain", "active"),
            self._member(organization, "Kabir Shah", "FG-1003", trainer, None, 94, "fat_loss", "inactive"),
            self._member(organization, "Meera Iyer", "FG-1004", trainer, None, 68, "maintenance", "active"),
            self._member(organization, "Rohan Kapoor", "FG-1005", trainer, None, 76, "muscle_gain", "frozen"),
        ]
        memberships = [
            self._member_membership(organization, members[0], quarterly, -52, 38, models.MembershipStatus.active.value),
            self._member_membership(organization, members[1], monthly, -23, 7, models.MembershipStatus.active.value),
            self._member_membership(organization, members[2], monthly, -45, -4, models.MembershipStatus.expired.value),
            self._member_membership(organization, members[3], annual, -120, 245, models.MembershipStatus.active.value),
            self._member_membership(organization, members[4], quarterly, -80, 10, models.MembershipStatus.paused.value),
        ]

        self._payments(organization, members, memberships)
        for member in members:
            self._goals(member, trainer)
            self._attendance(member)
            self._training(member)
            self._body_metrics(member, trainer)
            WorkoutPlanner(self.db).generate_week(member)
            DietPlanner(self.db).generate_week(member)

        self.db.flush()
        risk_service = RetentionIntelligenceService(self.db)
        for member in members:
            risk_service.snapshot_member_risk(member)
        RetentionAutomationService(self.db).daily_actions(organization.id, persist=True)
        self.db.commit()

        session = create_session(self.db, owner)
        return {
            "token": session.token,
            "account": {"id": owner.id, "email": owner.email, "created_at": owner.created_at.isoformat()},
            "profile": None,
            "organization": {"id": organization.id, "name": organization.name, "slug": organization.slug},
            "credentials": {
                "owner": {"email": owner.email, "password": DEMO_PASSWORD},
                "admin": {"email": admin.email, "password": DEMO_PASSWORD},
                "trainer": {"email": trainer.email, "password": DEMO_PASSWORD},
                "member": {"email": member_account.email, "password": DEMO_PASSWORD},
            },
        }

    def _account(self, email: str) -> models.Account:
        normalized = normalize_email(email)
        account = self.db.query(models.Account).filter(models.Account.email == normalized).first()
        if account:
            return account
        account = models.Account(email=normalized, password_hash=hash_password(DEMO_PASSWORD))
        self.db.add(account)
        self.db.flush()
        return account

    def _organization(self) -> models.Organization:
        organization = self.db.query(models.Organization).filter(models.Organization.slug == "fitgen-demo-gym").first()
        if organization:
            return organization
        organization = models.Organization(
            name="FitGen Performance Club",
            slug="fitgen-demo-gym",
            legal_name="FitGen Performance Club Pvt Ltd",
            phone="+91 90000 10001",
            email="ops@fitgen.demo",
            address="Indiranagar, Bengaluru",
        )
        self.db.add(organization)
        self.db.flush()
        return organization

    def _membership(self, organization: models.Organization, account: models.Account, role: str) -> None:
        existing = (
            self.db.query(models.OrganizationMembership)
            .filter(models.OrganizationMembership.organization_id == organization.id, models.OrganizationMembership.account_id == account.id)
            .first()
        )
        if existing:
            existing.role = role
            existing.active = True
            return
        self.db.add(models.OrganizationMembership(organization_id=organization.id, account_id=account.id, role=role))

    def _plan(self, organization: models.Organization, name: str, duration_days: int, price: float) -> models.MembershipPlan:
        plan = (
            self.db.query(models.MembershipPlan)
            .filter(models.MembershipPlan.organization_id == organization.id, models.MembershipPlan.name == name)
            .first()
        )
        if plan:
            return plan
        plan = models.MembershipPlan(organization_id=organization.id, name=name, duration_days=duration_days, price_amount=price, description="Demo membership plan")
        self.db.add(plan)
        self.db.flush()
        return plan

    def _member(
        self,
        organization: models.Organization,
        name: str,
        code: str,
        trainer: models.Account,
        account: models.Account | None,
        weight: float,
        goal: str,
        status: str,
    ) -> models.UserProfile:
        member = (
            self.db.query(models.UserProfile)
            .filter(models.UserProfile.organization_id == organization.id, models.UserProfile.member_code == code)
            .first()
        )
        if member:
            return member
        member = models.UserProfile(
            account_id=account.id if account else None,
            organization_id=organization.id,
            assigned_trainer_id=trainer.id,
            member_code=code,
            status=status,
            joined_on=date.today() - timedelta(days=95),
            name=name,
            age=31,
            height_cm=174,
            weight_kg=weight,
            fitness_goal=goal,
            diet_preference="non_veg",
            budget_amount=260,
            budget_period="daily",
            location="Bengaluru, India",
            gym_type="premium_gym",
        )
        self.db.add(member)
        self.db.flush()
        return member

    def _member_membership(
        self,
        organization: models.Organization,
        member: models.UserProfile,
        plan: models.MembershipPlan,
        start_offset: int,
        end_offset: int,
        status: str,
    ) -> models.MemberMembership:
        existing = (
            self.db.query(models.MemberMembership)
            .filter(models.MemberMembership.organization_id == organization.id, models.MemberMembership.member_id == member.id)
            .order_by(models.MemberMembership.id.desc())
            .first()
        )
        if existing:
            return existing
        membership = models.MemberMembership(
            organization_id=organization.id,
            member_id=member.id,
            plan_id=plan.id,
            starts_on=date.today() + timedelta(days=start_offset),
            ends_on=date.today() + timedelta(days=end_offset),
            status=status,
            notes="Seeded demo membership",
        )
        self.db.add(membership)
        self.db.flush()
        return membership

    def _payments(self, organization: models.Organization, members: list[models.UserProfile], memberships: list[models.MemberMembership]) -> None:
        if self.db.query(models.Payment).filter(models.Payment.organization_id == organization.id).first():
            return
        for index, member in enumerate(members):
            membership = memberships[index]
            amount = membership.plan.price_amount if membership.plan else 3000
            self.db.add(
                models.Payment(
                    organization_id=organization.id,
                    member_id=member.id,
                    membership_id=membership.id,
                    amount=amount,
                    status=models.PaymentStatus.overdue.value if index in {1, 2} else models.PaymentStatus.paid.value,
                    due_on=date.today() - timedelta(days=5) if index in {1, 2} else date.today() - timedelta(days=20),
                    paid_on=None if index in {1, 2} else date.today() - timedelta(days=18),
                    method="upi",
                    reference=f"DEMO-{index + 1}",
                )
            )

    def _goals(self, member: models.UserProfile, trainer: models.Account) -> None:
        if self.db.query(models.Goal).filter(models.Goal.member_id == member.id).first():
            return
        self.db.add(
            models.Goal(
                organization_id=member.organization_id,
                member_id=member.id,
                assigned_trainer_id=trainer.id,
                goal_type=models.GoalType.consistency.value,
                title="Attend 12 sessions this month",
                status=models.GoalStatus.active.value,
                target_value=12,
                current_value=7 if member.status == models.MemberStatus.active.value else 2,
                unit="sessions",
                starts_on=date.today() - timedelta(days=20),
                target_date=date.today() + timedelta(days=10),
            )
        )

    def _attendance(self, member: models.UserProfile) -> None:
        if self.db.query(models.AttendanceCheckin).filter(models.AttendanceCheckin.member_id == member.id).first():
            return
        days = [2, 5, 8, 12, 16, 22] if member.status == models.MemberStatus.active.value else [34, 41]
        for days_ago in days:
            self.db.add(
                models.AttendanceCheckin(
                    organization_id=member.organization_id,
                    member_id=member.id,
                    checked_in_at=datetime.utcnow() - timedelta(days=days_ago),
                    method=models.AttendanceMethod.qr.value,
                    recorded_by_account_id=member.assigned_trainer_id,
                )
            )

    def _training(self, member: models.UserProfile) -> None:
        if self.db.query(models.WorkoutLog).filter(models.WorkoutLog.user_id == member.id).first():
            return
        entries = 8 if member.status == models.MemberStatus.active.value else 2
        for index in range(entries):
            self.db.add(
                models.WorkoutLog(
                    user_id=member.id,
                    organization_id=member.organization_id,
                    exercise_name=["Goblet Squat", "Bench Press", "Lat Pulldown", "Romanian Deadlift"][index % 4],
                    performed_on=date.today() - timedelta(days=entries - index + 2),
                    sets_completed=3,
                    reps_completed=10 + index,
                    weight_kg=22.5 + index * 2,
                    completed=index % 5 != 0,
                    perceived_effort=7,
                )
            )

    def _body_metrics(self, member: models.UserProfile, trainer: models.Account) -> None:
        if self.db.query(models.BodyMetricSnapshot).filter(models.BodyMetricSnapshot.member_id == member.id).first():
            return
        self.db.add(
            models.BodyMetricSnapshot(
                organization_id=member.organization_id,
                member_id=member.id,
                measured_on=date.today() - timedelta(days=60),
                weight_kg=member.weight_kg + 3,
                body_fat_pct=27,
                waist_cm=94,
                recorded_by_account_id=trainer.id,
            )
        )
        self.db.add(
            models.BodyMetricSnapshot(
                organization_id=member.organization_id,
                member_id=member.id,
                measured_on=date.today() - timedelta(days=5),
                weight_kg=member.weight_kg,
                body_fat_pct=24,
                waist_cm=89,
                recorded_by_account_id=trainer.id,
            )
        )
        self.db.add(
            models.TransformationMilestone(
                organization_id=member.organization_id,
                member_id=member.id,
                trainer_account_id=trainer.id,
                milestone_type="consistency",
                title="Completed first transformation block",
                achieved_on=date.today() - timedelta(days=7),
                value=8,
                unit="sessions",
                notes="Demo milestone",
            )
        )
