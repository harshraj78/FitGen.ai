from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

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

WEEK_TEMPLATE = [
    ("Mon", "Lower Strength", ["Lower Strength", "Posterior Chain", "Core"]),
    ("Tue", "Upper Push", ["Upper Push", "Shoulders", "Arms"]),
    ("Wed", "Conditioning", ["Conditioning", "Core"]),
    ("Thu", "Upper Pull", ["Upper Pull", "Posterior Chain", "Arms"]),
    ("Fri", "Full Body", ["Lower Strength", "Upper Push", "Upper Pull", "Core"]),
    ("Sat", "Recovery", ["Conditioning", "Core"]),
]


class WorkoutPlanner:
    def __init__(self, db: Session):
        self.db = db

    def generate_week(self, user: models.UserProfile, week_start: date | None = None) -> models.WorkoutPlan:
        week_start = week_start or self._monday(date.today())
        available = EQUIPMENT_BY_GYM.get(user.gym_type, EQUIPMENT_BY_GYM["home"])
        metrics = self._performance_metrics(user.id)
        modifier, rationale = self._intensity_modifier(user, metrics)

        plan = models.WorkoutPlan(
            user_id=user.id,
            week_start=week_start,
            title=f"{user.name}'s adaptive week: {user.fitness_goal.replace('_', ' ')}",
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
        days: dict[int, dict] = {}
        for exercise in sorted(plan.exercises, key=lambda item: (item.day_index, item.id)):
            days.setdefault(
                exercise.day_index,
                {"day": exercise.day_name, "focus": exercise.focus, "exercises": []},
            )
            days[exercise.day_index]["exercises"].append(
                {
                    "id": exercise.id,
                    "name": exercise.exercise_name,
                    "equipment": exercise.equipment,
                    "sets": exercise.sets,
                    "target_reps": exercise.target_reps,
                    "target_weight_kg": exercise.target_weight_kg,
                    "notes": exercise.notes,
                }
            )
        return {
            "id": plan.id,
            "week_start": plan.week_start.isoformat(),
            "title": plan.title,
            "intensity_modifier": plan.intensity_modifier,
            "rationale": plan.rationale,
            "days": list(days.values()),
        }

    def current_plan(self, user_id: int) -> models.WorkoutPlan | None:
        return (
            self.db.query(models.WorkoutPlan)
            .filter(models.WorkoutPlan.user_id == user_id)
            .order_by(desc(models.WorkoutPlan.week_start), desc(models.WorkoutPlan.id))
            .first()
        )

    def _select_exercise(self, focus: str, available: set[str]) -> dict:
        candidates = [item for item in EXERCISE_LIBRARY if item["focus"] == focus]
        for item in candidates:
            if item["equipment"] in available:
                return item
        fallback_name = candidates[0]["fallback"] if candidates else "Bodyweight Circuit"
        return {"name": fallback_name, "focus": focus, "equipment": "bodyweight", "fallback": fallback_name}

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
            "completion_rate": completed / total if total else 1,
            "average_effort": effort_total / total if total else 7,
            "best_weight_by_exercise": dict(best_weight_by_exercise),
            "recent_feedback": [item.signal for item in feedback],
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
