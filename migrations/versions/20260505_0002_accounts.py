"""Add accounts and sessions.

Revision ID: 20260505_0002
Revises: 20260505_0001
Create Date: 2026-05-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260505_0002"
down_revision: str | None = "20260505_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "accounts" not in existing_tables:
        op.create_table(
            "accounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_accounts_email"), "accounts", ["email"], unique=True)

    if "account_sessions" not in existing_tables:
        op.create_table(
            "account_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("token", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_account_sessions_account_id"), "account_sessions", ["account_id"], unique=False)
        op.create_index(op.f("ix_account_sessions_token"), "account_sessions", ["token"], unique=True)

    user_profile_columns = {column["name"] for column in inspector.get_columns("user_profiles")}
    if "account_id" not in user_profile_columns:
        with op.batch_alter_table("user_profiles") as batch_op:
            batch_op.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
            batch_op.create_index(op.f("ix_user_profiles_account_id"), ["account_id"], unique=False)
            batch_op.create_foreign_key("fk_user_profiles_account_id_accounts", "accounts", ["account_id"], ["id"])
            batch_op.create_unique_constraint("uq_user_profiles_account_name", ["account_id", "name"])


def downgrade() -> None:
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_constraint("uq_user_profiles_account_name", type_="unique")
        batch_op.drop_constraint("fk_user_profiles_account_id_accounts", type_="foreignkey")
        batch_op.drop_index(op.f("ix_user_profiles_account_id"))
        batch_op.drop_column("account_id")
    op.drop_index(op.f("ix_account_sessions_token"), table_name="account_sessions")
    op.drop_index(op.f("ix_account_sessions_account_id"), table_name="account_sessions")
    op.drop_table("account_sessions")
    op.drop_index(op.f("ix_accounts_email"), table_name="accounts")
    op.drop_table("accounts")
