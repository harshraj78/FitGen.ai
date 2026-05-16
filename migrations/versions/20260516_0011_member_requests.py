"""Add member request workflow.

Revision ID: 20260516_0011
Revises: 20260516_0010
Create Date: 2026-05-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0011"
down_revision: str | None = "20260516_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "member_requests" in tables:
        return
    op.create_table(
        "member_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("resolution_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by_account_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_account_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["user_profiles.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["reviewed_by_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["created_at", "created_by_account_id", "member_id", "organization_id", "request_type", "reviewed_by_account_id", "status"]:
        op.create_index(op.f(f"ix_member_requests_{column}"), "member_requests", [column], unique=False)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "member_requests" not in set(inspector.get_table_names()):
        return
    for column in ["status", "reviewed_by_account_id", "request_type", "organization_id", "member_id", "created_by_account_id", "created_at"]:
        op.drop_index(op.f(f"ix_member_requests_{column}"), table_name="member_requests")
    op.drop_table("member_requests")
