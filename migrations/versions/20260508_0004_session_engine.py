"""Add workout session engine.

Revision ID: 20260508_0004
Revises: 20260505_0003
Create Date: 2026-05-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260508_0004"
down_revision: str | None = "20260505_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "workout_sessions" not in tables:
        op.create_table(
            "workout_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("workout_plan_id", sa.Integer(), nullable=True),
            sa.Column("day_index", sa.Integer(), nullable=True),
            sa.Column("planned_for", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("started_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("session_rpe", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=False),
            sa.Column("completion_rate", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
            sa.ForeignKeyConstraint(["workout_plan_id"], ["workout_plans.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_workout_sessions_user_id"), "workout_sessions", ["user_id"], unique=False)
        op.create_index(op.f("ix_workout_sessions_workout_plan_id"), "workout_sessions", ["workout_plan_id"], unique=False)
        op.create_index(op.f("ix_workout_sessions_status"), "workout_sessions", ["status"], unique=False)

    if "readiness_checkins" not in tables:
        op.create_table(
            "readiness_checkins",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("energy", sa.Integer(), nullable=True),
            sa.Column("sleep_quality", sa.Integer(), nullable=True),
            sa.Column("soreness", sa.Integer(), nullable=True),
            sa.Column("stress", sa.Integer(), nullable=True),
            sa.Column("pain", sa.Integer(), nullable=True),
            sa.Column("pain_notes", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["workout_sessions.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("session_id"),
        )
        op.create_index(op.f("ix_readiness_checkins_session_id"), "readiness_checkins", ["session_id"], unique=False)
        op.create_index(op.f("ix_readiness_checkins_user_id"), "readiness_checkins", ["user_id"], unique=False)

    if "workout_session_exercises" not in tables:
        op.create_table(
            "workout_session_exercises",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("planned_exercise_id", sa.Integer(), nullable=True),
            sa.Column("exercise_name", sa.String(length=140), nullable=False),
            sa.Column("order_index", sa.Integer(), nullable=False),
            sa.Column("target_sets", sa.Integer(), nullable=False),
            sa.Column("target_reps", sa.String(length=40), nullable=False),
            sa.Column("target_weight_kg", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("skip_reason", sa.String(length=80), nullable=False),
            sa.Column("notes", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["planned_exercise_id"], ["workout_exercises.id"]),
            sa.ForeignKeyConstraint(["session_id"], ["workout_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_workout_session_exercises_session_id"), "workout_session_exercises", ["session_id"], unique=False)
        op.create_index(
            op.f("ix_workout_session_exercises_planned_exercise_id"),
            "workout_session_exercises",
            ["planned_exercise_id"],
            unique=False,
        )
        op.create_index(op.f("ix_workout_session_exercises_status"), "workout_session_exercises", ["status"], unique=False)

    workout_log_columns = {column["name"] for column in inspector.get_columns("workout_logs")}
    workout_log_indexes = {index["name"] for index in inspector.get_indexes("workout_logs")}
    if "session_id" not in workout_log_columns:
        with op.batch_alter_table("workout_logs") as batch_op:
            batch_op.add_column(sa.Column("session_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_workout_logs_session_id_workout_sessions", "workout_sessions", ["session_id"], ["id"])
            batch_op.create_index(op.f("ix_workout_logs_session_id"), ["session_id"], unique=False)
    elif op.f("ix_workout_logs_session_id") not in workout_log_indexes:
        with op.batch_alter_table("workout_logs") as batch_op:
            batch_op.create_index(op.f("ix_workout_logs_session_id"), ["session_id"], unique=False)

    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "performed_sets" not in tables:
        op.create_table(
            "performed_sets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_exercise_id", sa.Integer(), nullable=False),
            sa.Column("workout_log_id", sa.Integer(), nullable=True),
            sa.Column("set_number", sa.Integer(), nullable=False),
            sa.Column("reps", sa.Integer(), nullable=False),
            sa.Column("weight_kg", sa.Float(), nullable=False),
            sa.Column("perceived_effort", sa.Integer(), nullable=False),
            sa.Column("completed", sa.Boolean(), nullable=False),
            sa.Column("pain_flag", sa.Boolean(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["session_exercise_id"], ["workout_session_exercises.id"]),
            sa.ForeignKeyConstraint(["workout_log_id"], ["workout_logs.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_performed_sets_session_exercise_id"), "performed_sets", ["session_exercise_id"], unique=False)
        op.create_index(op.f("ix_performed_sets_workout_log_id"), "performed_sets", ["workout_log_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_performed_sets_workout_log_id"), table_name="performed_sets")
    op.drop_index(op.f("ix_performed_sets_session_exercise_id"), table_name="performed_sets")
    op.drop_table("performed_sets")

    with op.batch_alter_table("workout_logs") as batch_op:
        batch_op.drop_index(op.f("ix_workout_logs_session_id"))
        batch_op.drop_constraint("fk_workout_logs_session_id_workout_sessions", type_="foreignkey")
        batch_op.drop_column("session_id")

    op.drop_index(op.f("ix_workout_session_exercises_status"), table_name="workout_session_exercises")
    op.drop_index(op.f("ix_workout_session_exercises_planned_exercise_id"), table_name="workout_session_exercises")
    op.drop_index(op.f("ix_workout_session_exercises_session_id"), table_name="workout_session_exercises")
    op.drop_table("workout_session_exercises")

    op.drop_index(op.f("ix_readiness_checkins_user_id"), table_name="readiness_checkins")
    op.drop_index(op.f("ix_readiness_checkins_session_id"), table_name="readiness_checkins")
    op.drop_table("readiness_checkins")

    op.drop_index(op.f("ix_workout_sessions_status"), table_name="workout_sessions")
    op.drop_index(op.f("ix_workout_sessions_workout_plan_id"), table_name="workout_sessions")
    op.drop_index(op.f("ix_workout_sessions_user_id"), table_name="workout_sessions")
    op.drop_table("workout_sessions")
