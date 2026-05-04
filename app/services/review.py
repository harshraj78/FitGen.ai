from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models


class WeeklyReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create_review(self, user: models.UserProfile, week_start: date | None = None) -> models.WeeklyReview:
        week_start = week_start or self._monday(date.today())
        week_end = week_start + timedelta(days=6)
        logs = (
            self.db.query(models.WorkoutLog)
            .filter(
                models.WorkoutLog.user_id == user.id,
                models.WorkoutLog.performed_on >= week_start,
                models.WorkoutLog.performed_on <= week_end,
            )
            .all()
        )
        previous_logs = (
            self.db.query(models.WorkoutLog)
            .filter(
                models.WorkoutLog.user_id == user.id,
                models.WorkoutLog.performed_on >= week_start - timedelta(days=7),
                models.WorkoutLog.performed_on < week_start,
            )
            .all()
        )
        completion_rate = sum(1 for log in logs if log.completed) / len(logs) if logs else 0
        strength_delta = self._strength_delta(previous_logs, logs)
        weak_lift = self._weakest_lift(logs)

        if completion_rate < 0.65:
            summary = "Workout completion was low this week."
            adjustments = "Next week should reduce total sets by about 10-15% and keep exercise selection familiar."
        elif strength_delta < -2:
            summary = f"{weak_lift} performance dropped compared with the previous week."
            adjustments = f"Reduce {weak_lift} volume next week and keep load stable until reps recover."
        elif strength_delta > 2:
            summary = "Strength trend improved across logged lifts."
            adjustments = "Apply small progressive overload to primary lifts while keeping effort below 9/10."
        else:
            summary = "Performance was stable with no major regression."
            adjustments = "Keep the next plan close to baseline and progress only completed lifts."

        review = models.WeeklyReview(
            user_id=user.id,
            week_start=week_start,
            completion_rate=round(completion_rate, 2),
            strength_delta=round(strength_delta, 2),
            summary=summary,
            adjustments=adjustments,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def latest_review(self, user_id: int) -> models.WeeklyReview | None:
        return (
            self.db.query(models.WeeklyReview)
            .filter(models.WeeklyReview.user_id == user_id)
            .order_by(desc(models.WeeklyReview.week_start), desc(models.WeeklyReview.id))
            .first()
        )

    def serialize_review(self, review: models.WeeklyReview | None) -> dict | None:
        if not review:
            return None
        return {
            "id": review.id,
            "week_start": review.week_start.isoformat(),
            "completion_rate": review.completion_rate,
            "strength_delta": review.strength_delta,
            "summary": review.summary,
            "adjustments": review.adjustments,
        }

    def _strength_delta(self, previous_logs: list[models.WorkoutLog], logs: list[models.WorkoutLog]) -> float:
        previous = self._average_load(previous_logs)
        current = self._average_load(logs)
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100

    def _average_load(self, logs: list[models.WorkoutLog]) -> float:
        weighted = [log.weight_kg * max(log.reps_completed, 1) for log in logs if log.completed]
        return sum(weighted) / len(weighted) if weighted else 0

    def _weakest_lift(self, logs: list[models.WorkoutLog]) -> str:
        if not logs:
            return "primary lift"
        return sorted(logs, key=lambda log: (log.completed, log.weight_kg * log.reps_completed))[0].exercise_name

    def _monday(self, current: date) -> date:
        return current - timedelta(days=current.weekday())
