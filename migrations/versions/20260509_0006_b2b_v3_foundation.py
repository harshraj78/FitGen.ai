"""Add B2B multi-tenant v3 foundation.

Revision ID: 20260509_0006
Revises: 20260508_0005
Create Date: 2026-05-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260509_0006"
down_revision: str | None = "20260508_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "organizations" not in tables:
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("slug", sa.String(length=120), nullable=False),
            sa.Column("legal_name", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("timezone", sa.String(length=80), nullable=False, server_default="Asia/Kolkata"),
            sa.Column("phone", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("email", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("address", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index(op.f("ix_organizations_name"), "organizations", ["name"], unique=False)
        op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)
        op.create_index(op.f("ix_organizations_status"), "organizations", ["status"], unique=False)

    if "organization_memberships" not in tables:
        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(length=40), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "account_id", name="uq_org_membership_account"),
        )
        op.create_index(op.f("ix_organization_memberships_account_id"), "organization_memberships", ["account_id"], unique=False)
        op.create_index(op.f("ix_organization_memberships_active"), "organization_memberships", ["active"], unique=False)
        op.create_index(op.f("ix_organization_memberships_organization_id"), "organization_memberships", ["organization_id"], unique=False)
        op.create_index(op.f("ix_organization_memberships_role"), "organization_memberships", ["role"], unique=False)

    _add_user_profile_columns(inspector)
    _add_workout_plan_columns(inspector)

    if "membership_plans" not in tables:
        op.create_table(
            "membership_plans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("duration_days", sa.Integer(), nullable=False),
            sa.Column("price_amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(length=12), nullable=False, server_default="INR"),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "name", name="uq_membership_plans_org_name"),
        )
        op.create_index(op.f("ix_membership_plans_active"), "membership_plans", ["active"], unique=False)
        op.create_index(op.f("ix_membership_plans_organization_id"), "membership_plans", ["organization_id"], unique=False)

    if "member_memberships" not in tables:
        op.create_table(
            "member_memberships",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("plan_id", sa.Integer(), nullable=True),
            sa.Column("starts_on", sa.Date(), nullable=False),
            sa.Column("ends_on", sa.Date(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("renewal_of_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["plan_id"], ["membership_plans.id"]),
            sa.ForeignKeyConstraint(["renewal_of_id"], ["member_memberships.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_member_memberships_ends_on"), "member_memberships", ["ends_on"], unique=False)
        op.create_index(op.f("ix_member_memberships_member_id"), "member_memberships", ["member_id"], unique=False)
        op.create_index(op.f("ix_member_memberships_organization_id"), "member_memberships", ["organization_id"], unique=False)
        op.create_index(op.f("ix_member_memberships_plan_id"), "member_memberships", ["plan_id"], unique=False)
        op.create_index(op.f("ix_member_memberships_status"), "member_memberships", ["status"], unique=False)

    if "payments" not in tables:
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("membership_id", sa.Integer(), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(length=12), nullable=False, server_default="INR"),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("due_on", sa.Date(), nullable=True),
            sa.Column("paid_on", sa.Date(), nullable=True),
            sa.Column("method", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("reference", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["membership_id"], ["member_memberships.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_payments_due_on"), "payments", ["due_on"], unique=False)
        op.create_index(op.f("ix_payments_member_id"), "payments", ["member_id"], unique=False)
        op.create_index(op.f("ix_payments_membership_id"), "payments", ["membership_id"], unique=False)
        op.create_index(op.f("ix_payments_organization_id"), "payments", ["organization_id"], unique=False)
        op.create_index(op.f("ix_payments_paid_on"), "payments", ["paid_on"], unique=False)
        op.create_index(op.f("ix_payments_status"), "payments", ["status"], unique=False)

    if "attendance_checkins" not in tables:
        op.create_table(
            "attendance_checkins",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("checked_in_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("method", sa.String(length=30), nullable=False, server_default="manual"),
            sa.Column("recorded_by_account_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["recorded_by_account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_attendance_checkins_checked_in_at"), "attendance_checkins", ["checked_in_at"], unique=False)
        op.create_index(op.f("ix_attendance_checkins_member_id"), "attendance_checkins", ["member_id"], unique=False)
        op.create_index(op.f("ix_attendance_checkins_organization_id"), "attendance_checkins", ["organization_id"], unique=False)
        op.create_index(op.f("ix_attendance_checkins_recorded_by_account_id"), "attendance_checkins", ["recorded_by_account_id"], unique=False)

    if "goals" not in tables:
        op.create_table(
            "goals",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("created_by_account_id", sa.Integer(), nullable=True),
            sa.Column("assigned_trainer_id", sa.Integer(), nullable=True),
            sa.Column("goal_type", sa.String(length=40), nullable=False, server_default="custom"),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("description", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
            sa.Column("target_value", sa.Float(), nullable=True),
            sa.Column("current_value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("starts_on", sa.Date(), nullable=True),
            sa.Column("target_date", sa.Date(), nullable=True),
            sa.Column("achieved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["assigned_trainer_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_goals_assigned_trainer_id"), "goals", ["assigned_trainer_id"], unique=False)
        op.create_index(op.f("ix_goals_created_by_account_id"), "goals", ["created_by_account_id"], unique=False)
        op.create_index(op.f("ix_goals_goal_type"), "goals", ["goal_type"], unique=False)
        op.create_index(op.f("ix_goals_member_id"), "goals", ["member_id"], unique=False)
        op.create_index(op.f("ix_goals_organization_id"), "goals", ["organization_id"], unique=False)
        op.create_index(op.f("ix_goals_status"), "goals", ["status"], unique=False)
        op.create_index(op.f("ix_goals_target_date"), "goals", ["target_date"], unique=False)

    if "goal_milestones" not in tables:
        op.create_table(
            "goal_milestones",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("goal_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=160), nullable=False),
            sa.Column("target_value", sa.Float(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_goal_milestones_goal_id"), "goal_milestones", ["goal_id"], unique=False)

    if "audit_logs" not in tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("actor_account_id", sa.Integer(), nullable=True),
            sa.Column("action", sa.String(length=120), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["actor_account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
        op.create_index(op.f("ix_audit_logs_actor_account_id"), "audit_logs", ["actor_account_id"], unique=False)
        op.create_index(op.f("ix_audit_logs_entity_id"), "audit_logs", ["entity_id"], unique=False)
        op.create_index(op.f("ix_audit_logs_organization_id"), "audit_logs", ["organization_id"], unique=False)


def downgrade() -> None:
    for index_name in ["ix_audit_logs_organization_id", "ix_audit_logs_entity_id", "ix_audit_logs_actor_account_id", "ix_audit_logs_action"]:
        op.drop_index(index_name, table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_goal_milestones_goal_id"), table_name="goal_milestones")
    op.drop_table("goal_milestones")

    for index_name in [
        "ix_goals_target_date",
        "ix_goals_status",
        "ix_goals_organization_id",
        "ix_goals_member_id",
        "ix_goals_goal_type",
        "ix_goals_created_by_account_id",
        "ix_goals_assigned_trainer_id",
    ]:
        op.drop_index(index_name, table_name="goals")
    op.drop_table("goals")

    for index_name in [
        "ix_attendance_checkins_recorded_by_account_id",
        "ix_attendance_checkins_organization_id",
        "ix_attendance_checkins_member_id",
        "ix_attendance_checkins_checked_in_at",
    ]:
        op.drop_index(index_name, table_name="attendance_checkins")
    op.drop_table("attendance_checkins")

    for index_name in ["ix_payments_status", "ix_payments_paid_on", "ix_payments_organization_id", "ix_payments_membership_id", "ix_payments_member_id", "ix_payments_due_on"]:
        op.drop_index(index_name, table_name="payments")
    op.drop_table("payments")

    for index_name in ["ix_member_memberships_status", "ix_member_memberships_plan_id", "ix_member_memberships_organization_id", "ix_member_memberships_member_id", "ix_member_memberships_ends_on"]:
        op.drop_index(index_name, table_name="member_memberships")
    op.drop_table("member_memberships")

    op.drop_index(op.f("ix_membership_plans_organization_id"), table_name="membership_plans")
    op.drop_index(op.f("ix_membership_plans_active"), table_name="membership_plans")
    op.drop_table("membership_plans")

    with op.batch_alter_table("workout_plans") as batch_op:
        batch_op.drop_index(op.f("ix_workout_plans_reviewed_by_account_id"))
        batch_op.drop_index(op.f("ix_workout_plans_generated_by_account_id"))
        batch_op.drop_index(op.f("ix_workout_plans_status"))
        batch_op.drop_index(op.f("ix_workout_plans_organization_id"))
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("trainer_notes")
        batch_op.drop_column("status")
        batch_op.drop_column("reviewed_by_account_id")
        batch_op.drop_column("generated_by_account_id")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_index(op.f("ix_user_profiles_status"))
        batch_op.drop_index(op.f("ix_user_profiles_assigned_trainer_id"))
        batch_op.drop_index(op.f("ix_user_profiles_organization_id"))
        batch_op.drop_column("joined_on")
        batch_op.drop_column("status")
        batch_op.drop_column("member_code")
        batch_op.drop_column("assigned_trainer_id")
        batch_op.drop_column("organization_id")

    for index_name in [
        "ix_organization_memberships_role",
        "ix_organization_memberships_organization_id",
        "ix_organization_memberships_active",
        "ix_organization_memberships_account_id",
    ]:
        op.drop_index(index_name, table_name="organization_memberships")
    op.drop_table("organization_memberships")

    op.drop_index(op.f("ix_organizations_status"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_name"), table_name="organizations")
    op.drop_table("organizations")


def _add_user_profile_columns(inspector: sa.Inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    with op.batch_alter_table("user_profiles") as batch_op:
        if "organization_id" not in columns:
            batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_user_profiles_organization_id_organizations", "organizations", ["organization_id"], ["id"])
            batch_op.create_index(op.f("ix_user_profiles_organization_id"), ["organization_id"], unique=False)
        if "assigned_trainer_id" not in columns:
            batch_op.add_column(sa.Column("assigned_trainer_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_user_profiles_assigned_trainer_id_accounts", "accounts", ["assigned_trainer_id"], ["id"])
            batch_op.create_index(op.f("ix_user_profiles_assigned_trainer_id"), ["assigned_trainer_id"], unique=False)
        if "member_code" not in columns:
            batch_op.add_column(sa.Column("member_code", sa.String(length=80), nullable=False, server_default=""))
        if "status" not in columns:
            batch_op.add_column(sa.Column("status", sa.String(length=30), nullable=False, server_default="active"))
            batch_op.create_index(op.f("ix_user_profiles_status"), ["status"], unique=False)
        if "joined_on" not in columns:
            batch_op.add_column(sa.Column("joined_on", sa.Date(), nullable=True))


def _add_workout_plan_columns(inspector: sa.Inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns("workout_plans")}
    with op.batch_alter_table("workout_plans") as batch_op:
        if "organization_id" not in columns:
            batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_workout_plans_organization_id_organizations", "organizations", ["organization_id"], ["id"])
            batch_op.create_index(op.f("ix_workout_plans_organization_id"), ["organization_id"], unique=False)
        if "generated_by_account_id" not in columns:
            batch_op.add_column(sa.Column("generated_by_account_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_workout_plans_generated_by_account_id_accounts", "accounts", ["generated_by_account_id"], ["id"])
            batch_op.create_index(op.f("ix_workout_plans_generated_by_account_id"), ["generated_by_account_id"], unique=False)
        if "reviewed_by_account_id" not in columns:
            batch_op.add_column(sa.Column("reviewed_by_account_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_workout_plans_reviewed_by_account_id_accounts", "accounts", ["reviewed_by_account_id"], ["id"])
            batch_op.create_index(op.f("ix_workout_plans_reviewed_by_account_id"), ["reviewed_by_account_id"], unique=False)
        if "status" not in columns:
            batch_op.add_column(sa.Column("status", sa.String(length=40), nullable=False, server_default="trainer_approved"))
            batch_op.create_index(op.f("ix_workout_plans_status"), ["status"], unique=False)
        if "trainer_notes" not in columns:
            batch_op.add_column(sa.Column("trainer_notes", sa.Text(), nullable=False, server_default=""))
        if "reviewed_at" not in columns:
            batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(), nullable=True))
