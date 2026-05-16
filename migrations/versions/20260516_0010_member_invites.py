"""Add member invite tracking fields.

Revision ID: 20260516_0010
Revises: 20260515_0009
Create Date: 2026-05-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0010"
down_revision: str | None = "20260515_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    if "invite_token_hash" not in columns:
        op.add_column("user_profiles", sa.Column("invite_token_hash", sa.String(length=128), nullable=False, server_default=""))
        op.create_index(op.f("ix_user_profiles_invite_token_hash"), "user_profiles", ["invite_token_hash"], unique=False)
    if "invited_at" not in columns:
        op.add_column("user_profiles", sa.Column("invited_at", sa.DateTime(), nullable=True))
    if "invite_accepted_at" not in columns:
        op.add_column("user_profiles", sa.Column("invite_accepted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    if "invite_accepted_at" in columns:
        op.drop_column("user_profiles", "invite_accepted_at")
    if "invited_at" in columns:
        op.drop_column("user_profiles", "invited_at")
    if "invite_token_hash" in columns:
        op.drop_index(op.f("ix_user_profiles_invite_token_hash"), table_name="user_profiles")
        op.drop_column("user_profiles", "invite_token_hash")
