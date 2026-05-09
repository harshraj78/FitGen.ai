"""Add business operations retention tables.

Revision ID: 20260510_0008
Revises: 20260509_0007
Create Date: 2026-05-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260510_0008"
down_revision: str | None = "20260509_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "renewal_risk_snapshots" not in tables:
        op.create_table(
            "renewal_risk_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("membership_id", sa.Integer(), nullable=True),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("level", sa.String(length=20), nullable=False),
            sa.Column("signals_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("forecast_renewal_on", sa.Date(), nullable=True),
            sa.Column("revenue_at_risk", sa.Float(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["membership_id"], ["member_memberships.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["created_at", "forecast_renewal_on", "level", "member_id", "membership_id", "organization_id", "score"]:
            op.create_index(op.f(f"ix_renewal_risk_snapshots_{column}"), "renewal_risk_snapshots", [column], unique=False)

    if "retention_workflows" not in tables:
        op.create_table(
            "retention_workflows",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("assigned_account_id", sa.Integer(), nullable=True),
            sa.Column("workflow_type", sa.String(length=60), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
            sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("due_on", sa.Date(), nullable=True),
            sa.Column("source_entity_type", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("source_entity_id", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["assigned_account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in [
            "assigned_account_id",
            "created_at",
            "due_on",
            "member_id",
            "organization_id",
            "priority",
            "source_entity_id",
            "status",
            "workflow_type",
        ]:
            op.create_index(op.f(f"ix_retention_workflows_{column}"), "retention_workflows", [column], unique=False)

    if "body_metric_snapshots" not in tables:
        op.create_table(
            "body_metric_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("measured_on", sa.Date(), nullable=False),
            sa.Column("weight_kg", sa.Float(), nullable=True),
            sa.Column("body_fat_pct", sa.Float(), nullable=True),
            sa.Column("waist_cm", sa.Float(), nullable=True),
            sa.Column("chest_cm", sa.Float(), nullable=True),
            sa.Column("hip_cm", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("recorded_by_account_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["recorded_by_account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["measured_on", "member_id", "organization_id", "recorded_by_account_id"]:
            op.create_index(op.f(f"ix_body_metric_snapshots_{column}"), "body_metric_snapshots", [column], unique=False)

    if "transformation_milestones" not in tables:
        op.create_table(
            "transformation_milestones",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("trainer_account_id", sa.Integer(), nullable=True),
            sa.Column("milestone_type", sa.String(length=60), nullable=False),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("achieved_on", sa.Date(), nullable=False),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["trainer_account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ["achieved_on", "member_id", "milestone_type", "organization_id", "trainer_account_id"]:
            op.create_index(op.f(f"ix_transformation_milestones_{column}"), "transformation_milestones", [column], unique=False)


def downgrade() -> None:
    for table_name, columns in [
        ("transformation_milestones", ["trainer_account_id", "organization_id", "milestone_type", "member_id", "achieved_on"]),
        ("body_metric_snapshots", ["recorded_by_account_id", "organization_id", "member_id", "measured_on"]),
        (
            "retention_workflows",
            [
                "workflow_type",
                "status",
                "source_entity_id",
                "priority",
                "organization_id",
                "member_id",
                "due_on",
                "created_at",
                "assigned_account_id",
            ],
        ),
        ("renewal_risk_snapshots", ["score", "organization_id", "membership_id", "member_id", "level", "forecast_renewal_on", "created_at"]),
    ]:
        for column in columns:
            op.drop_index(op.f(f"ix_{table_name}_{column}"), table_name=table_name)
        op.drop_table(table_name)
