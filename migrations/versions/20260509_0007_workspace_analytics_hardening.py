"""Add trainer workspace analytics hardening.

Revision ID: 20260509_0007
Revises: 20260509_0006
Create Date: 2026-05-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260509_0007"
down_revision: str | None = "20260509_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    _add_org_column("workout_logs", "user_id", inspector)
    _add_org_column("feedback", "user_id", inspector)
    _add_org_column("workout_sessions", "user_id", inspector)
    _add_org_column("readiness_checkins", "user_id", inspector)
    _add_audit_actor_user(inspector)

    if "notification_events" not in tables:
        op.create_table(
            "notification_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notification_events_entity_id"), "notification_events", ["entity_id"], unique=False)
        op.create_index(op.f("ix_notification_events_event_type"), "notification_events", ["event_type"], unique=False)
        op.create_index(op.f("ix_notification_events_organization_id"), "notification_events", ["organization_id"], unique=False)

    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("event_id", sa.Integer(), nullable=True),
            sa.Column("recipient_account_id", sa.Integer(), nullable=True),
            sa.Column("recipient_user_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("channel", sa.String(length=30), nullable=False, server_default="in_app"),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("delivered_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["event_id"], ["notification_events.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["recipient_account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["recipient_user_id"], ["user_profiles.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notifications_channel"), "notifications", ["channel"], unique=False)
        op.create_index(op.f("ix_notifications_event_id"), "notifications", ["event_id"], unique=False)
        op.create_index(op.f("ix_notifications_event_type"), "notifications", ["event_type"], unique=False)
        op.create_index(op.f("ix_notifications_organization_id"), "notifications", ["organization_id"], unique=False)
        op.create_index(op.f("ix_notifications_read_at"), "notifications", ["read_at"], unique=False)
        op.create_index(op.f("ix_notifications_recipient_account_id"), "notifications", ["recipient_account_id"], unique=False)
        op.create_index(op.f("ix_notifications_recipient_user_id"), "notifications", ["recipient_user_id"], unique=False)

    if "notification_preferences" not in tables:
        op.create_table(
            "notification_preferences",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("channel", sa.String(length=30), nullable=False, server_default="in_app"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "account_id", "event_type", "channel", name="uq_notification_pref_scope"),
        )
        op.create_index(op.f("ix_notification_preferences_account_id"), "notification_preferences", ["account_id"], unique=False)
        op.create_index(op.f("ix_notification_preferences_channel"), "notification_preferences", ["channel"], unique=False)
        op.create_index(op.f("ix_notification_preferences_enabled"), "notification_preferences", ["enabled"], unique=False)
        op.create_index(op.f("ix_notification_preferences_event_type"), "notification_preferences", ["event_type"], unique=False)
        op.create_index(op.f("ix_notification_preferences_organization_id"), "notification_preferences", ["organization_id"], unique=False)

    if "ai_explainability_records" not in tables:
        op.create_table(
            "ai_explainability_records",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("workout_plan_id", sa.Integer(), nullable=True),
            sa.Column("entity_type", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=True),
            sa.Column("reason_code", sa.String(length=80), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["workout_plan_id"], ["workout_plans.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_explainability_records_entity_id"), "ai_explainability_records", ["entity_id"], unique=False)
        op.create_index(op.f("ix_ai_explainability_records_entity_type"), "ai_explainability_records", ["entity_type"], unique=False)
        op.create_index(op.f("ix_ai_explainability_records_organization_id"), "ai_explainability_records", ["organization_id"], unique=False)
        op.create_index(op.f("ix_ai_explainability_records_reason_code"), "ai_explainability_records", ["reason_code"], unique=False)
        op.create_index(op.f("ix_ai_explainability_records_user_id"), "ai_explainability_records", ["user_id"], unique=False)
        op.create_index(op.f("ix_ai_explainability_records_workout_plan_id"), "ai_explainability_records", ["workout_plan_id"], unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_ai_explainability_records_workout_plan_id",
        "ix_ai_explainability_records_user_id",
        "ix_ai_explainability_records_reason_code",
        "ix_ai_explainability_records_organization_id",
        "ix_ai_explainability_records_entity_type",
        "ix_ai_explainability_records_entity_id",
    ]:
        op.drop_index(index_name, table_name="ai_explainability_records")
    op.drop_table("ai_explainability_records")

    for index_name in [
        "ix_notification_preferences_organization_id",
        "ix_notification_preferences_event_type",
        "ix_notification_preferences_enabled",
        "ix_notification_preferences_channel",
        "ix_notification_preferences_account_id",
    ]:
        op.drop_index(index_name, table_name="notification_preferences")
    op.drop_table("notification_preferences")

    for index_name in [
        "ix_notifications_recipient_user_id",
        "ix_notifications_recipient_account_id",
        "ix_notifications_read_at",
        "ix_notifications_organization_id",
        "ix_notifications_event_type",
        "ix_notifications_event_id",
        "ix_notifications_channel",
    ]:
        op.drop_index(index_name, table_name="notifications")
    op.drop_table("notifications")

    op.drop_index(op.f("ix_notification_events_organization_id"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_event_type"), table_name="notification_events")
    op.drop_index(op.f("ix_notification_events_entity_id"), table_name="notification_events")
    op.drop_table("notification_events")

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_index(op.f("ix_audit_logs_actor_user_id"))
        batch_op.drop_constraint("fk_audit_logs_actor_user_id_user_profiles", type_="foreignkey")
        batch_op.drop_column("actor_user_id")

    for table_name in ["readiness_checkins", "workout_sessions", "feedback", "workout_logs"]:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(op.f(f"ix_{table_name}_organization_id"))
            batch_op.drop_constraint(f"fk_{table_name}_organization_id_organizations", type_="foreignkey")
            batch_op.drop_column("organization_id")


def _add_org_column(table_name: str, user_column: str, inspector: sa.Inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if "organization_id" in columns:
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(f"fk_{table_name}_organization_id_organizations", "organizations", ["organization_id"], ["id"])
        batch_op.create_index(op.f(f"ix_{table_name}_organization_id"), ["organization_id"], unique=False)
    op.get_bind().execute(
        sa.text(
            f"update {table_name} set organization_id = "
            f"(select user_profiles.organization_id from user_profiles where user_profiles.id = {table_name}.{user_column}) "
            "where organization_id is null"
        )
    )


def _add_audit_actor_user(inspector: sa.Inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns("audit_logs")}
    if "actor_user_id" in columns:
        return
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_audit_logs_actor_user_id_user_profiles", "user_profiles", ["actor_user_id"], ["id"])
        batch_op.create_index(op.f("ix_audit_logs_actor_user_id"), ["actor_user_id"], unique=False)
