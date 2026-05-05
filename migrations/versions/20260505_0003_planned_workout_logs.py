"""Link workout logs to planned exercises.

Revision ID: 20260505_0003
Revises: 20260505_0002
Create Date: 2026-05-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260505_0003"
down_revision: str | None = "20260505_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("workout_logs")}
    indexes = {index["name"] for index in inspector.get_indexes("workout_logs")}

    if "planned_exercise_id" not in columns:
        with op.batch_alter_table("workout_logs") as batch_op:
            batch_op.add_column(sa.Column("planned_exercise_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_workout_logs_planned_exercise_id_workout_exercises",
                "workout_exercises",
                ["planned_exercise_id"],
                ["id"],
            )
            batch_op.create_index(op.f("ix_workout_logs_planned_exercise_id"), ["planned_exercise_id"], unique=False)
    elif op.f("ix_workout_logs_planned_exercise_id") not in indexes:
        with op.batch_alter_table("workout_logs") as batch_op:
            batch_op.create_index(op.f("ix_workout_logs_planned_exercise_id"), ["planned_exercise_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("workout_logs") as batch_op:
        batch_op.drop_index(op.f("ix_workout_logs_planned_exercise_id"))
        batch_op.drop_constraint("fk_workout_logs_planned_exercise_id_workout_exercises", type_="foreignkey")
        batch_op.drop_column("planned_exercise_id")
