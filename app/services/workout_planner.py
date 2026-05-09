from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models


EQUIPMENT_BY_GYM = {
    "home": {"bodyweight", "dumbbell", "resistance_band", "backpack"},
    "local_gym": {"bodyweight", "dumbbell", "barbell", "bench", "cable", "leg_press"},
    "premium_gym": {
        "bodyweight",
        "dumbbell",
        "barbell",
        "bench",
        "cable",
        "leg_press",
        "smith_machine",
        "lat_pulldown",
        "machine",
    },
}

EXERCISE_LIBRARY = [
    {"name": "Goblet Squat", "focus": "Lower Strength", "equipment": "dumbbell", "fallback": "Backpack Squat"},
    {"name": "Barbell Back Squat", "focus": "Lower Strength", "equipment": "barbell", "fallback": "Goblet Squat"},
    {"name": "Leg Press", "focus": "Lower Strength", "equipment": "leg_press", "fallback": "Goblet Squat"},
    {"name": "Push-up", "focus": "Upper Push", "equipment": "bodyweight", "fallback": "Incline Push-up"},
    {"name": "Dumbbell Bench Press", "focus": "Upper Push", "equipment": "dumbbell", "fallback": "Push-up"},
    {"name": "Machine Chest Press", "focus": "Upper Push", "equipment": "machine", "fallback": "Dumbbell Bench Press"},
    {"name": "One-arm Dumbbell Row", "focus": "Upper Pull", "equipment": "dumbbell", "fallback": "Band Row"},
    {"name": "Lat Pulldown", "focus": "Upper Pull", "equipment": "lat_pulldown", "fallback": "Band Lat Pulldown"},
    {"name": "Romanian Deadlift", "focus": "Posterior Chain", "equipment": "barbell", "fallback": "Dumbbell Romanian Deadlift"},
    {"name": "Dumbbell Romanian Deadlift", "focus": "Posterior Chain", "equipment": "dumbbell", "fallback": "Backpack Good Morning"},
    {"name": "Overhead Press", "focus": "Shoulders", "equipment": "dumbbell", "fallback": "Pike Push-up"},
    {"name": "Cable Triceps Pressdown", "focus": "Arms", "equipment": "cable", "fallback": "Close-grip Push-up"},
    {"name": "Dumbbell Curl", "focus": "Arms", "equipment": "dumbbell", "fallback": "Band Curl"},
    {"name": "Plank", "focus": "Core", "equipment": "bodyweight", "fallback": "Dead Bug"},
    {"name": "Farmer Carry", "focus": "Conditioning", "equipment": "dumbbell", "fallback": "Loaded Backpack Carry"},
]

EXERCISE_METADATA = {
    "Lower Strength": ("squat", "quads, glutes", "knee"),
    "Upper Push": ("horizontal_push", "chest, triceps", "shoulder"),
    "Upper Pull": ("horizontal_pull", "lats, upper back", "shoulder, elbow"),
    "Posterior Chain": ("hinge", "hamstrings, glutes", "spine, hamstring"),
    "Shoulders": ("vertical_push", "shoulders, triceps", "shoulder"),
    "Arms": ("elbow_isolation", "arms", "elbow"),
    "Core": ("anti_extension", "core", "shoulder"),
    "Conditioning": ("loaded_carry", "grip, core", "spine"),
}

WEEK_TEMPLATE = [
    ("Mon", "Lower Strength", ["Lower Strength", "Posterior Chain", "Core"]),
    ("Tue", "Upper Push", ["Upper Push", "Shoulders", "Arms"]),
    ("Wed", "Conditioning", ["Conditioning", "Core"]),
    ("Thu", "Upper Pull", ["Upper Pull", "Posterior Chain", "Arms"]),
    ("Fri", "Full Body", ["Lower Strength", "Upper Push", "Upper Pull", "Core"]),
    ("Sat", "Recovery", ["Conditioning", "Core"]),
]

DAY_FOCUS_MAP = {day_name: day_focus for day_name, day_focus, _ in WEEK_TEMPLATE}

EQUIPMENT_ALIASES = {
    "dumbbell": {"dumbbell", "dumbbells", "db", "adjustable dumbbell"},
    "barbell": {"barbell", "rod", "olympic bar", "bar"},
    "bench": {"bench", "flat bench", "adjustable bench"},
    "cable": {"cable", "cable machine", "functional trainer"},
    "leg_press": {"leg press", "leg press machine"},
    "lat_pulldown": {"lat pulldown", "pulldown", "lat machine"},
    "machine": {"machine", "chest press machine", "selectorized machine"},
    "smith_machine": {"smith machine", "smith"},
    "resistance_band": {"band", "bands", "resistance band", "resistance bands"},
    "backpack": {"backpack", "weighted backpack"},
    "bodyweight": {"bodyweight", "floor", "mat"},
}


class WorkoutPlanner:
    def __init__(self, db: Session):
        self.db = db

    def generate_week(self, user: models.UserProfile, week_start: date | None = None) -> models.WorkoutPlan:
        self._ensure_exercise_catalog()
        week_start = week_start or self._monday(date.today())
        available = EQUIPMENT_BY_GYM.get(user.gym_type, EQUIPMENT_BY_GYM["home"])
        metrics = self._performance_metrics(user.id)
        modifier, rationale = self._intensity_modifier(user, metrics)

        plan = models.WorkoutPlan(
            user_id=user.id,
            organization_id=user.organization_id,
            week_start=week_start,
            title=f"{user.name}'s adaptive week: {user.fitness_goal.replace('_', ' ')}",
            status=self._initial_plan_status(user),
            intensity_modifier=modifier,
            rationale=rationale,
        )
        self.db.add(plan)
        self.db.flush()

        for day_index, (day_name, day_focus, focus_blocks) in enumerate(WEEK_TEMPLATE, start=1):
            for focus in focus_blocks:
                exercise = self._select_exercise(focus, available)
                sets = self._sets_for_goal(user.fitness_goal, day_focus, modifier)
                reps = self._reps_for_goal(user.fitness_goal)
                last_weight = metrics["best_weight_by_exercise"].get(exercise["name"], 0)
                target_weight = self._next_weight(last_weight, modifier, exercise["equipment"])
                note = self._exercise_note(exercise, available, modifier)
                self.db.add(
                    models.WorkoutExercise(
                        plan_id=plan.id,
                        exercise_id=exercise.get("id"),
                        day_index=day_index,
                        day_name=day_name,
                        focus=day_focus,
                        exercise_name=exercise["name"],
                        equipment=exercise["equipment"],
                        sets=sets,
                        target_reps=reps,
                        target_weight_kg=target_weight,
                        notes=note,
                    )
                )

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def serialize_plan(self, plan: models.WorkoutPlan | None) -> dict | None:
        if not plan:
            return None
        exercise_statuses = self._exercise_statuses(plan)
        days: dict[int, dict] = {}
        for exercise in sorted(plan.exercises, key=lambda item: (item.day_index, item.id)):
            days.setdefault(
                exercise.day_index,
                {"day": exercise.day_name, "focus": exercise.focus, "exercises": []},
            )
            days[exercise.day_index]["exercises"].append(
                {
                    "id": exercise.id,
                    "exercise_id": exercise.exercise_id,
                    "name": exercise.exercise_name,
                    "equipment": exercise.equipment,
                    "sets": exercise.sets,
                    "target_reps": exercise.target_reps,
                    "target_weight_kg": exercise.target_weight_kg,
                    "notes": exercise.notes,
                    "status": exercise_statuses.get(exercise.id, {}).get("status", "pending"),
                    "last_log": exercise_statuses.get(exercise.id),
                }
            )
        return {
            "id": plan.id,
            "week_start": plan.week_start.isoformat(),
            "title": plan.title,
            "status": plan.status,
            "organization_id": plan.organization_id,
            "reviewed_by_account_id": plan.reviewed_by_account_id,
            "reviewed_at": plan.reviewed_at.isoformat() if plan.reviewed_at else None,
            "trainer_notes": plan.trainer_notes,
            "intensity_modifier": plan.intensity_modifier,
            "rationale": plan.rationale,
            "planned_exercise_count": len(plan.exercises),
            "days": list(days.values()),
        }

    def current_plan(self, user_id: int) -> models.WorkoutPlan | None:
        return (
            self.db.query(models.WorkoutPlan)
            .filter(models.WorkoutPlan.user_id == user_id)
            .order_by(desc(models.WorkoutPlan.week_start), desc(models.WorkoutPlan.id))
            .first()
        )

    def generate_ai_ready_proposal(self, user: models.UserProfile, equipment_text: str) -> dict[str, Any]:
        self._ensure_exercise_catalog()
        available = self.parse_equipment_text(equipment_text) or EQUIPMENT_BY_GYM.get(user.gym_type, EQUIPMENT_BY_GYM["home"])
        metrics = self._performance_metrics(user.id)
        modifier, rationale = self._intensity_modifier(user, metrics)
        days: list[dict[str, Any]] = []

        for day_name, day_focus, focus_blocks in WEEK_TEMPLATE:
            for focus in focus_blocks:
                exercise = self._select_exercise(focus, available)
                sets = self._sets_for_goal(user.fitness_goal, day_focus, modifier)
                reps = self._reps_for_goal(user.fitness_goal)
                last_weight = metrics["best_weight_by_exercise"].get(exercise["name"], 0)
                days.append(
                    {
                        "day": day_name,
                        "focus": day_focus,
                        "name": exercise["name"],
                        "equipment": exercise["equipment"],
                        "sets": sets,
                        "target_reps": reps,
                        "target_weight_kg": self._next_weight(last_weight, modifier, exercise["equipment"]),
                        "notes": self._exercise_note(exercise, available, modifier),
                    }
                )

        return {
            "title": f"{user.name}'s equipment-aware week",
            "rationale": f"{rationale}. Built from available equipment: {', '.join(sorted(available))}.",
            "equipment_summary": sorted(available),
            "days": days,
        }

    def apply_plan_proposal(self, user: models.UserProfile, proposal: dict[str, Any], week_start: date | None = None) -> models.WorkoutPlan:
        self._ensure_exercise_catalog()
        week_start = week_start or self._monday(date.today())
        plan = models.WorkoutPlan(
            user_id=user.id,
            organization_id=user.organization_id,
            week_start=week_start,
            title=proposal["title"],
            status=self._initial_plan_status(user),
            intensity_modifier=1.0,
            rationale=proposal["rationale"],
        )
        self.db.add(plan)
        self.db.flush()

        for index, exercise in enumerate(proposal["days"], start=1):
            day_name = exercise["day"]
            self.db.add(
                models.WorkoutExercise(
                    plan_id=plan.id,
                    exercise_id=self._exercise_id_by_name(exercise["name"]),
                    day_index=self._day_index(day_name, index),
                    day_name=day_name,
                    focus=exercise["focus"],
                    exercise_name=exercise["name"],
                    equipment=exercise["equipment"],
                    sets=exercise["sets"],
                    target_reps=exercise["target_reps"],
                    target_weight_kg=exercise["target_weight_kg"],
                    notes=exercise["notes"],
                )
            )

        self.db.commit()
        self.db.refresh(plan)
        return plan

    def parse_equipment_text(self, equipment_text: str) -> set[str]:
        parts = [part.strip().lower() for raw in equipment_text.replace("\n", ",").split(",") for part in [raw.strip()] if part.strip()]
        available = {"bodyweight"}
        for part in parts:
            for canonical, aliases in EQUIPMENT_ALIASES.items():
                if part == canonical or part in aliases or canonical.replace("_", " ") in part:
                    available.add(canonical)
        return available

    def _select_exercise(self, focus: str, available: set[str]) -> dict:
        candidates = [item for item in EXERCISE_LIBRARY if item["focus"] == focus]
        for item in candidates:
            if item["equipment"] in available:
                return {**item, "id": self._exercise_id_by_name(item["name"])}
        fallback_name = candidates[0]["fallback"] if candidates else "Bodyweight Circuit"
        return {
            "id": self._exercise_id_by_name(fallback_name),
            "name": fallback_name,
            "focus": focus,
            "equipment": self._equipment_for_name(fallback_name, "bodyweight"),
            "fallback": fallback_name,
        }

    def _ensure_exercise_catalog(self) -> None:
        existing = {name for (name,) in self.db.query(models.Exercise.name).all()}
        exercise_rows = list(EXERCISE_LIBRARY)
        fallback_names = {item["fallback"] for item in EXERCISE_LIBRARY}
        known_names = {item["name"] for item in exercise_rows}
        for fallback_name in sorted(fallback_names - known_names):
            source = next(item for item in EXERCISE_LIBRARY if item["fallback"] == fallback_name)
            exercise_rows.append(
                {
                    "name": fallback_name,
                    "focus": source["focus"],
                    "equipment": self._equipment_for_name(fallback_name, "bodyweight"),
                    "fallback": fallback_name,
                }
            )

        for item in exercise_rows:
            if item["name"] in existing:
                continue
            movement_pattern, muscles, stress_tags = EXERCISE_METADATA.get(item["focus"], ("general", "", ""))
            self.db.add(
                models.Exercise(
                    name=item["name"],
                    focus=item["focus"],
                    movement_pattern=movement_pattern,
                    equipment=item["equipment"],
                    difficulty="beginner",
                    primary_muscles=muscles,
                    joint_stress_tags=stress_tags,
                )
            )
        self.db.flush()

        name_to_exercise = {exercise.name: exercise for exercise in self.db.query(models.Exercise).all()}
        existing_pairs = {
            (source, substitute)
            for source, substitute in self.db.query(
                models.ExerciseSubstitution.source_exercise_id,
                models.ExerciseSubstitution.substitute_exercise_id,
            ).all()
        }
        for item in EXERCISE_LIBRARY:
            source = name_to_exercise.get(item["name"])
            substitute = name_to_exercise.get(item["fallback"])
            if not source or not substitute or source.id == substitute.id or (source.id, substitute.id) in existing_pairs:
                continue
            self.db.add(
                models.ExerciseSubstitution(
                    source_exercise_id=source.id,
                    substitute_exercise_id=substitute.id,
                    reason="equipment_fallback",
                )
            )
        self.db.flush()

    def _exercise_id_by_name(self, name: str) -> int | None:
        exercise = self.db.query(models.Exercise).filter(models.Exercise.name == name).first()
        return exercise.id if exercise else None

    def _equipment_for_name(self, name: str, default: str) -> str:
        lowered = name.lower()
        if "band" in lowered:
            return "resistance_band"
        if "backpack" in lowered:
            return "backpack"
        if "dumbbell" in lowered:
            return "dumbbell"
        if "barbell" in lowered:
            return "barbell"
        if "cable" in lowered:
            return "cable"
        if "machine" in lowered:
            return "machine"
        return default

    def _performance_metrics(self, user_id: int) -> dict:
        since = date.today() - timedelta(days=21)
        logs = (
            self.db.query(models.WorkoutLog)
            .filter(models.WorkoutLog.user_id == user_id, models.WorkoutLog.performed_on >= since)
            .all()
        )
        feedback = (
            self.db.query(models.Feedback)
            .filter(models.Feedback.user_id == user_id)
            .order_by(desc(models.Feedback.created_at))
            .limit(10)
            .all()
        )
        current_plan = self.current_plan(user_id)
        linked_completion = self._linked_completion_metrics(current_plan)

        best_weight_by_exercise: dict[str, float] = defaultdict(float)
        completed = 0
        total = 0
        effort_total = 0
        for log in logs:
            total += 1
            completed += int(log.completed)
            effort_total += log.perceived_effort
            best_weight_by_exercise[log.exercise_name] = max(best_weight_by_exercise[log.exercise_name], log.weight_kg)

        return {
            "completion_rate": linked_completion["completion_rate"] if linked_completion["total"] else (completed / total if total else 1),
            "average_effort": effort_total / total if total else 7,
            "best_weight_by_exercise": dict(best_weight_by_exercise),
            "recent_feedback": [item.signal for item in feedback],
        }

    def _linked_completion_metrics(self, plan: models.WorkoutPlan | None) -> dict[str, float]:
        if not plan or not plan.exercises:
            return {"completed": 0, "total": 0, "completion_rate": 0}
        statuses = self._exercise_statuses(plan)
        completed_ids = {exercise_id for exercise_id, status in statuses.items() if status["status"] == "completed"}
        exercise_ids = [exercise.id for exercise in plan.exercises]
        total = len(exercise_ids)
        completed = len(completed_ids)
        return {"completed": completed, "total": total, "completion_rate": completed / total if total else 0}

    def _exercise_statuses(self, plan: models.WorkoutPlan) -> dict[int, dict]:
        exercise_ids = [exercise.id for exercise in plan.exercises]
        if not exercise_ids:
            return {}
        logs = (
            self.db.query(models.WorkoutLog)
            .filter(models.WorkoutLog.planned_exercise_id.in_(exercise_ids))
            .order_by(models.WorkoutLog.id.desc())
            .all()
        )
        latest_by_exercise: dict[int, models.WorkoutLog] = {}
        for log in logs:
            if log.planned_exercise_id is not None and log.planned_exercise_id not in latest_by_exercise:
                latest_by_exercise[log.planned_exercise_id] = log
        return {
            exercise_id: {
                "status": "completed" if log.completed else "skipped",
                "performed_on": log.performed_on.isoformat(),
                "sets_completed": log.sets_completed,
                "reps_completed": log.reps_completed,
                "weight_kg": log.weight_kg,
                "effort": log.perceived_effort,
            }
            for exercise_id, log in latest_by_exercise.items()
        }

    def _intensity_modifier(self, user: models.UserProfile, metrics: dict) -> tuple[float, str]:
        modifier = 1.0
        reasons: list[str] = []
        recent_feedback = metrics["recent_feedback"]

        if metrics["completion_rate"] < 0.65 or "missed_workout" in recent_feedback[:3]:
            modifier -= 0.12
            reasons.append("completion dropped, reducing volume")
        if "too_hard" in recent_feedback[:3] or metrics["average_effort"] >= 9:
            modifier -= 0.1
            reasons.append("recent effort was high, lowering intensity")
        if "too_easy" in recent_feedback[:3] and metrics["completion_rate"] >= 0.85:
            modifier += 0.08
            reasons.append("sessions were easy and completion is strong, applying progressive overload")
        if user.fitness_goal == "fat_loss":
            reasons.append("conditioning remains present for fat loss")
        if user.fitness_goal == "muscle_gain":
            modifier += 0.03
            reasons.append("muscle gain goal gets slightly higher strength volume")

        bounded = min(1.15, max(0.75, modifier))
        return bounded, "; ".join(reasons) or "stable progress, keeping plan near baseline"

    def _sets_for_goal(self, goal: str, focus: str, modifier: float) -> int:
        base = 3
        if goal == "muscle_gain":
            base = 4
        if goal == "fat_loss" and focus == "Conditioning":
            base = 4
        return max(2, min(5, round(base * modifier)))

    def _reps_for_goal(self, goal: str) -> str:
        if goal == "muscle_gain":
            return "8-12"
        if goal == "fat_loss":
            return "10-15"
        return "8-10"

    def _next_weight(self, last_weight: float, modifier: float, equipment: str) -> float:
        if equipment == "bodyweight" or last_weight <= 0:
            return 0
        overload = 1.025 if modifier <= 1 else 1.05
        return round(last_weight * overload * modifier, 1)

    def _exercise_note(self, exercise: dict, available: set[str], modifier: float) -> str:
        note = "Track last clean set; stop one rep before form breaks."
        if exercise["equipment"] not in available:
            note = f"Equipment fallback applied from {exercise['equipment']}."
        if modifier < 0.9:
            note += " Reduced this week due to fatigue or missed sessions."
        if modifier > 1.05:
            note += " Add load only if all target reps were clean last week."
        return note

    def _monday(self, current: date) -> date:
        return current - timedelta(days=current.weekday())

    def _day_index(self, day_name: str, fallback_index: int) -> int:
        for index, (template_day, _, _) in enumerate(WEEK_TEMPLATE, start=1):
            if template_day == day_name:
                return index
        return min(6, max(1, fallback_index))

    def _initial_plan_status(self, user: models.UserProfile) -> str:
        if user.organization_id and user.assigned_trainer_id:
            return models.PlanReviewStatus.pending_trainer_review.value
        if user.organization_id:
            return models.PlanReviewStatus.ai_generated.value
        return models.PlanReviewStatus.trainer_approved.value
