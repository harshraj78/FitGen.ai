"""Add member contact fields for automation.

Revision ID: 20260515_0009
Revises: 20260510_0008
Create Date: 2026-05-15
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0009"
down_revision: str | None = "20260510_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    if "phone" not in columns:
        op.add_column("user_profiles", sa.Column("phone", sa.String(length=40), nullable=False, server_default=""))
    if "email" not in columns:
        op.add_column("user_profiles", sa.Column("email", sa.String(length=255), nullable=False, server_default=""))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    if "email" in columns:
        op.drop_column("user_profiles", "email")
    if "phone" in columns:
        op.drop_column("user_profiles", "phone")
