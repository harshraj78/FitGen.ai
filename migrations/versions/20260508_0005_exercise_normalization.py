"""Add normalized exercise catalog.

Revision ID: 20260508_0005
Revises: 20260508_0004
Create Date: 2026-05-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260508_0005"
down_revision: str | None = "20260508_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEED_EXERCISES = [
    ("Goblet Squat", "Lower Strength", "squat", "dumbbell", "quads, glutes", "knee"),
    ("Barbell Back Squat", "Lower Strength", "squat", "barbell", "quads, glutes", "knee, spine"),
    ("Leg Press", "Lower Strength", "squat", "leg_press", "quads, glutes", "knee"),
    ("Backpack Squat", "Lower Strength", "squat", "backpack", "quads, glutes", "knee"),
    ("Push-up", "Upper Push", "horizontal_push", "bodyweight", "chest, triceps", "wrist, shoulder"),
    ("Incline Push-up", "Upper Push", "horizontal_push", "bodyweight", "chest, triceps", "wrist, shoulder"),
    ("Dumbbell Bench Press", "Upper Push", "horizontal_push", "dumbbell", "chest, triceps", "shoulder"),
    ("Machine Chest Press", "Upper Push", "horizontal_push", "machine", "chest, triceps", "shoulder"),
    ("One-arm Dumbbell Row", "Upper Pull", "horizontal_pull", "dumbbell", "lats, upper back", "elbow"),
    ("Band Row", "Upper Pull", "horizontal_pull", "resistance_band", "lats, upper back", "elbow"),
    ("Lat Pulldown", "Upper Pull", "vertical_pull", "lat_pulldown", "lats, biceps", "shoulder, elbow"),
    ("Band Lat Pulldown", "Upper Pull", "vertical_pull", "resistance_band", "lats, biceps", "shoulder, elbow"),
    ("Romanian Deadlift", "Posterior Chain", "hinge", "barbell", "hamstrings, glutes", "spine, hamstring"),
    ("Dumbbell Romanian Deadlift", "Posterior Chain", "hinge", "dumbbell", "hamstrings, glutes", "spine, hamstring"),
    ("Backpack Good Morning", "Posterior Chain", "hinge", "backpack", "hamstrings, glutes", "spine, hamstring"),
    ("Overhead Press", "Shoulders", "vertical_push", "dumbbell", "shoulders, triceps", "shoulder"),
    ("Pike Push-up", "Shoulders", "vertical_push", "bodyweight", "shoulders, triceps", "shoulder, wrist"),
    ("Cable Triceps Pressdown", "Arms", "elbow_extension", "cable", "triceps", "elbow"),
    ("Close-grip Push-up", "Arms", "elbow_extension", "bodyweight", "triceps, chest", "wrist, elbow"),
    ("Dumbbell Curl", "Arms", "elbow_flexion", "dumbbell", "biceps", "elbow"),
    ("Band Curl", "Arms", "elbow_flexion", "resistance_band", "biceps", "elbow"),
    ("Plank", "Core", "anti_extension", "bodyweight", "core", "shoulder"),
    ("Dead Bug", "Core", "anti_extension", "bodyweight", "core", ""),
    ("Farmer Carry", "Conditioning", "loaded_carry", "dumbbell", "grip, core", "spine"),
    ("Loaded Backpack Carry", "Conditioning", "loaded_carry", "backpack", "grip, core", "spine"),
]

SEED_SUBSTITUTIONS = [
    ("Goblet Squat", "Backpack Squat", "equipment_fallback"),
    ("Barbell Back Squat", "Goblet Squat", "equipment_fallback"),
    ("Leg Press", "Goblet Squat", "equipment_fallback"),
    ("Push-up", "Incline Push-up", "regression"),
    ("Dumbbell Bench Press", "Push-up", "equipment_fallback"),
    ("Machine Chest Press", "Dumbbell Bench Press", "equipment_fallback"),
    ("One-arm Dumbbell Row", "Band Row", "equipment_fallback"),
    ("Lat Pulldown", "Band Lat Pulldown", "equipment_fallback"),
    ("Romanian Deadlift", "Dumbbell Romanian Deadlift", "equipment_fallback"),
    ("Dumbbell Romanian Deadlift", "Backpack Good Morning", "equipment_fallback"),
    ("Overhead Press", "Pike Push-up", "equipment_fallback"),
    ("Cable Triceps Pressdown", "Close-grip Push-up", "equipment_fallback"),
    ("Dumbbell Curl", "Band Curl", "equipment_fallback"),
    ("Plank", "Dead Bug", "regression"),
    ("Farmer Carry", "Loaded Backpack Carry", "equipment_fallback"),
]


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "exercises" not in tables:
        op.create_table(
            "exercises",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=140), nullable=False),
            sa.Column("focus", sa.String(length=80), nullable=False),
            sa.Column("movement_pattern", sa.String(length=80), nullable=False),
            sa.Column("equipment", sa.String(length=80), nullable=False),
            sa.Column("difficulty", sa.String(length=40), nullable=False),
            sa.Column("primary_muscles", sa.String(length=200), nullable=False),
            sa.Column("joint_stress_tags", sa.String(length=200), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(op.f("ix_exercises_name"), "exercises", ["name"], unique=True)

    if "exercise_aliases" not in tables:
        op.create_table(
            "exercise_aliases",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("exercise_id", sa.Integer(), nullable=False),
            sa.Column("alias", sa.String(length=140), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("alias"),
        )
        op.create_index(op.f("ix_exercise_aliases_exercise_id"), "exercise_aliases", ["exercise_id"], unique=False)
        op.create_index(op.f("ix_exercise_aliases_alias"), "exercise_aliases", ["alias"], unique=True)

    if "exercise_substitutions" not in tables:
        op.create_table(
            "exercise_substitutions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_exercise_id", sa.Integer(), nullable=False),
            sa.Column("substitute_exercise_id", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(length=120), nullable=False),
            sa.Column("equipment_constraint", sa.String(length=80), nullable=False),
            sa.Column("pain_constraint", sa.String(length=120), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
            sa.ForeignKeyConstraint(["source_exercise_id"], ["exercises.id"]),
            sa.ForeignKeyConstraint(["substitute_exercise_id"], ["exercises.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_exercise_id", "substitute_exercise_id", name="uq_exercise_substitution_pair"),
        )
        op.create_index(op.f("ix_exercise_substitutions_source_exercise_id"), "exercise_substitutions", ["source_exercise_id"], unique=False)
        op.create_index(op.f("ix_exercise_substitutions_substitute_exercise_id"), "exercise_substitutions", ["substitute_exercise_id"], unique=False)

    exercise_table = sa.table(
        "exercises",
        sa.column("name", sa.String),
        sa.column("focus", sa.String),
        sa.column("movement_pattern", sa.String),
        sa.column("equipment", sa.String),
        sa.column("difficulty", sa.String),
        sa.column("primary_muscles", sa.String),
        sa.column("joint_stress_tags", sa.String),
    )
    existing = {row[0] for row in op.get_bind().execute(sa.text("select name from exercises")).fetchall()}
    rows = [
        {
            "name": name,
            "focus": focus,
            "movement_pattern": pattern,
            "equipment": equipment,
            "difficulty": "beginner",
            "primary_muscles": muscles,
            "joint_stress_tags": tags,
        }
        for name, focus, pattern, equipment, muscles, tags in SEED_EXERCISES
        if name not in existing
    ]
    if rows:
        op.bulk_insert(exercise_table, rows)

    columns = {column["name"] for column in inspector.get_columns("workout_exercises")}
    if "exercise_id" not in columns:
        with op.batch_alter_table("workout_exercises") as batch_op:
            batch_op.add_column(sa.Column("exercise_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_workout_exercises_exercise_id_exercises", "exercises", ["exercise_id"], ["id"])
            batch_op.create_index(op.f("ix_workout_exercises_exercise_id"), ["exercise_id"], unique=False)
    op.get_bind().execute(
        sa.text(
            "update workout_exercises set exercise_id = "
            "(select exercises.id from exercises where exercises.name = workout_exercises.exercise_name) "
            "where exercise_id is null"
        )
    )

    columns = {column["name"] for column in inspector.get_columns("workout_session_exercises")}
    if "exercise_id" not in columns:
        with op.batch_alter_table("workout_session_exercises") as batch_op:
            batch_op.add_column(sa.Column("exercise_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_workout_session_exercises_exercise_id_exercises", "exercises", ["exercise_id"], ["id"])
            batch_op.create_index(op.f("ix_workout_session_exercises_exercise_id"), ["exercise_id"], unique=False)
    op.get_bind().execute(
        sa.text(
            "update workout_session_exercises set exercise_id = "
            "(select exercises.id from exercises where exercises.name = workout_session_exercises.exercise_name) "
            "where exercise_id is null"
        )
    )

    name_to_id = {row[0]: row[1] for row in op.get_bind().execute(sa.text("select name, id from exercises")).fetchall()}
    substitution_table = sa.table(
        "exercise_substitutions",
        sa.column("source_exercise_id", sa.Integer),
        sa.column("substitute_exercise_id", sa.Integer),
        sa.column("reason", sa.String),
        sa.column("equipment_constraint", sa.String),
        sa.column("pain_constraint", sa.String),
    )
    existing_pairs = {
        (row[0], row[1])
        for row in op.get_bind().execute(sa.text("select source_exercise_id, substitute_exercise_id from exercise_substitutions")).fetchall()
    }
    substitution_rows = []
    for source, substitute, reason in SEED_SUBSTITUTIONS:
        pair = (name_to_id.get(source), name_to_id.get(substitute))
        if pair[0] and pair[1] and pair not in existing_pairs:
            substitution_rows.append(
                {
                    "source_exercise_id": pair[0],
                    "substitute_exercise_id": pair[1],
                    "reason": reason,
                    "equipment_constraint": "",
                    "pain_constraint": "",
                }
            )
    if substitution_rows:
        op.bulk_insert(substitution_table, substitution_rows)


def downgrade() -> None:
    with op.batch_alter_table("workout_session_exercises") as batch_op:
        batch_op.drop_index(op.f("ix_workout_session_exercises_exercise_id"))
        batch_op.drop_constraint("fk_workout_session_exercises_exercise_id_exercises", type_="foreignkey")
        batch_op.drop_column("exercise_id")

    with op.batch_alter_table("workout_exercises") as batch_op:
        batch_op.drop_index(op.f("ix_workout_exercises_exercise_id"))
        batch_op.drop_constraint("fk_workout_exercises_exercise_id_exercises", type_="foreignkey")
        batch_op.drop_column("exercise_id")

    op.drop_index(op.f("ix_exercise_substitutions_substitute_exercise_id"), table_name="exercise_substitutions")
    op.drop_index(op.f("ix_exercise_substitutions_source_exercise_id"), table_name="exercise_substitutions")
    op.drop_table("exercise_substitutions")
    op.drop_index(op.f("ix_exercise_aliases_alias"), table_name="exercise_aliases")
    op.drop_index(op.f("ix_exercise_aliases_exercise_id"), table_name="exercise_aliases")
    op.drop_table("exercise_aliases")
    op.drop_index(op.f("ix_exercises_name"), table_name="exercises")
    op.drop_table("exercises")
