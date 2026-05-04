"""Initial FitGen AI schema.

Revision ID: 20260505_0001
Revises:
Create Date: 2026-05-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260505_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("height_cm", sa.Float(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("fitness_goal", sa.String(length=40), nullable=False),
        sa.Column("diet_preference", sa.String(length=20), nullable=False),
        sa.Column("budget_amount", sa.Float(), nullable=False),
        sa.Column("budget_period", sa.String(length=20), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.Column("gym_type", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "diet_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("calories", sa.Integer(), nullable=False),
        sa.Column("protein_g", sa.Integer(), nullable=False),
        sa.Column("estimated_daily_cost", sa.Float(), nullable=False),
        sa.Column("meals_json", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diet_plans_user_id"), "diet_plans", ["user_id"], unique=False)
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("signal", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_user_id"), "feedback", ["user_id"], unique=False)
    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("completion_rate", sa.Float(), nullable=False),
        sa.Column("strength_delta", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("adjustments", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_weekly_reviews_user_id"), "weekly_reviews", ["user_id"], unique=False)
    op.create_table(
        "workout_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("exercise_name", sa.String(length=140), nullable=False),
        sa.Column("performed_on", sa.Date(), nullable=False),
        sa.Column("sets_completed", sa.Integer(), nullable=False),
        sa.Column("reps_completed", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("perceived_effort", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_logs_user_id"), "workout_logs", ["user_id"], unique=False)
    op.create_table(
        "workout_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("intensity_modifier", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_plans_user_id"), "workout_plans", ["user_id"], unique=False)
    op.create_table(
        "workout_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("day_name", sa.String(length=20), nullable=False),
        sa.Column("focus", sa.String(length=80), nullable=False),
        sa.Column("exercise_name", sa.String(length=140), nullable=False),
        sa.Column("equipment", sa.String(length=80), nullable=False),
        sa.Column("sets", sa.Integer(), nullable=False),
        sa.Column("target_reps", sa.String(length=40), nullable=False),
        sa.Column("target_weight_kg", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["workout_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workout_exercises_plan_id"), "workout_exercises", ["plan_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workout_exercises_plan_id"), table_name="workout_exercises")
    op.drop_table("workout_exercises")
    op.drop_index(op.f("ix_workout_plans_user_id"), table_name="workout_plans")
    op.drop_table("workout_plans")
    op.drop_index(op.f("ix_workout_logs_user_id"), table_name="workout_logs")
    op.drop_table("workout_logs")
    op.drop_index(op.f("ix_weekly_reviews_user_id"), table_name="weekly_reviews")
    op.drop_table("weekly_reviews")
    op.drop_index(op.f("ix_feedback_user_id"), table_name="feedback")
    op.drop_table("feedback")
    op.drop_index(op.f("ix_diet_plans_user_id"), table_name="diet_plans")
    op.drop_table("diet_plans")
    op.drop_table("user_profiles")
