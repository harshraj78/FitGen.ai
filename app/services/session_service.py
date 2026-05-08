from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models, schemas
from app.services.workout_planner import WorkoutPlanner


class WorkoutSessionService:
    def __init__(self, db: Session):
        self.db = db

    def start_session(self, user: models.UserProfile, payload: schemas.WorkoutSessionStart) -> models.WorkoutSession:
        active = self.get_active_session(user.id)
        if active:
            return active

        plan = self._plan_for_start(user.id, payload.workout_plan_id)
        day_index = payload.day_index or self._first_pending_day_index(plan) or 1
        planned_for = payload.planned_for or self._planned_date(plan, day_index)
        planned_exercises = [
            exercise
            for exercise in sorted(plan.exercises, key=lambda item: (item.day_index, item.id))
            if exercise.day_index == day_index
        ]
        if not planned_exercises:
            raise HTTPException(status_code=400, detail="Selected plan day has no exercises")

        session = models.WorkoutSession(
            user_id=user.id,
            workout_plan_id=plan.id,
            day_index=day_index,
            planned_for=planned_for,
            status=models.WorkoutSessionStatus.active.value,
            notes="",
            completion_rate=0,
        )
        self.db.add(session)
        self.db.flush()

        if payload.readiness:
            self.db.add(
                models.ReadinessCheckin(
                    session_id=session.id,
                    user_id=user.id,
                    **payload.readiness.model_dump(),
                )
            )

        for index, exercise in enumerate(planned_exercises, start=1):
            self.db.add(
                models.WorkoutSessionExercise(
                    session_id=session.id,
                    planned_exercise_id=exercise.id,
                    exercise_id=exercise.exercise_id,
                    exercise_name=exercise.exercise_name,
                    order_index=index,
                    target_sets=exercise.sets,
                    target_reps=exercise.target_reps,
                    target_weight_kg=exercise.target_weight_kg,
                    status=models.SessionExerciseStatus.pending.value,
                    notes=exercise.notes,
                )
            )

        self.db.commit()
        self.db.refresh(session)
        return session

    def get_active_session(self, user_id: int) -> models.WorkoutSession | None:
        return (
            self.db.query(models.WorkoutSession)
            .filter(
                models.WorkoutSession.user_id == user_id,
                models.WorkoutSession.status == models.WorkoutSessionStatus.active.value,
            )
            .order_by(desc(models.WorkoutSession.started_at), desc(models.WorkoutSession.id))
            .first()
        )

    def get_session(self, session_id: int, user_id: int | None = None) -> models.WorkoutSession:
        session = self.db.get(models.WorkoutSession, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        if user_id is not None and session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Session belongs to another user")
        return session

    def log_set(
        self,
        session: models.WorkoutSession,
        session_exercise_id: int,
        payload: schemas.PerformedSetCreate,
    ) -> models.WorkoutSession:
        self._require_active(session)
        session_exercise = self._session_exercise(session, session_exercise_id)
        if session_exercise.status == models.SessionExerciseStatus.skipped.value:
            raise HTTPException(status_code=400, detail="Cannot log sets for a skipped exercise")

        existing_sets = sorted(session_exercise.sets, key=lambda item: item.set_number)
        performed_set = models.PerformedSet(
            set_number=len(existing_sets) + 1,
            **payload.model_dump(),
        )
        session_exercise.sets.append(performed_set)
        session_exercise.status = (
            models.SessionExerciseStatus.completed.value
            if len(existing_sets) + 1 >= session_exercise.target_sets
            else models.SessionExerciseStatus.in_progress.value
        )
        self.db.flush()
        workout_log = self._sync_aggregate_log(session, session_exercise)
        performed_set.workout_log_id = workout_log.id
        self._refresh_completion(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def skip_exercise(
        self,
        session: models.WorkoutSession,
        session_exercise_id: int,
        payload: schemas.SessionExerciseSkip,
    ) -> models.WorkoutSession:
        self._require_active(session)
        session_exercise = self._session_exercise(session, session_exercise_id)
        if session_exercise.sets:
            raise HTTPException(status_code=400, detail="Exercise already has logged sets; finish it instead of skipping")
        session_exercise.status = models.SessionExerciseStatus.skipped.value
        session_exercise.skip_reason = payload.reason
        session_exercise.notes = payload.notes or session_exercise.notes
        self._sync_aggregate_log(session, session_exercise)
        self._refresh_completion(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def finish_session(self, session: models.WorkoutSession, payload: schemas.WorkoutSessionFinish) -> models.WorkoutSession:
        self._require_active(session)
        pending = [
            exercise
            for exercise in session.exercises
            if exercise.status in {models.SessionExerciseStatus.pending.value, models.SessionExerciseStatus.in_progress.value}
        ]
        if pending:
            raise HTTPException(status_code=400, detail="Finish every exercise or skip remaining exercises first")
        session.status = models.WorkoutSessionStatus.completed.value
        session.finished_at = datetime.utcnow()
        session.session_rpe = payload.session_rpe
        session.notes = payload.notes
        self._refresh_completion(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def abandon_session(self, session: models.WorkoutSession) -> models.WorkoutSession:
        self._require_active(session)
        session.status = models.WorkoutSessionStatus.abandoned.value
        session.finished_at = datetime.utcnow()
        self._refresh_completion(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def serialize_session(self, session: models.WorkoutSession | None) -> dict | None:
        if not session:
            return None
        return {
            "id": session.id,
            "user_id": session.user_id,
            "workout_plan_id": session.workout_plan_id,
            "day_index": session.day_index,
            "planned_for": session.planned_for.isoformat() if session.planned_for else None,
            "status": session.status,
            "started_at": session.started_at.isoformat(),
            "finished_at": session.finished_at.isoformat() if session.finished_at else None,
            "session_rpe": session.session_rpe,
            "notes": session.notes,
            "completion_rate": session.completion_rate,
            "readiness": self._readiness_dict(session.readiness),
            "exercises": [
                self._session_exercise_dict(exercise)
                for exercise in sorted(session.exercises, key=lambda item: item.order_index)
            ],
            "safety": self._safety_notes(session),
        }

    def _plan_for_start(self, user_id: int, plan_id: int | None) -> models.WorkoutPlan:
        if plan_id is not None:
            plan = self.db.get(models.WorkoutPlan, plan_id)
            if not plan or plan.user_id != user_id:
                raise HTTPException(status_code=400, detail="Workout plan does not belong to this user")
            return plan
        plan = WorkoutPlanner(self.db).current_plan(user_id)
        if not plan:
            raise HTTPException(status_code=400, detail="User has no workout plan")
        return plan

    def _first_pending_day_index(self, plan: models.WorkoutPlan) -> int | None:
        serialized = WorkoutPlanner(self.db).serialize_plan(plan)
        if not serialized:
            return None
        for index, day in enumerate(serialized["days"], start=1):
            if any(exercise["status"] == "pending" for exercise in day["exercises"]):
                return index
        return 1

    def _planned_date(self, plan: models.WorkoutPlan, day_index: int) -> date:
        from datetime import timedelta

        return plan.week_start + timedelta(days=max(0, day_index - 1))

    def _require_active(self, session: models.WorkoutSession) -> None:
        if session.status != models.WorkoutSessionStatus.active.value:
            raise HTTPException(status_code=400, detail="Session is not active")

    def _session_exercise(self, session: models.WorkoutSession, session_exercise_id: int) -> models.WorkoutSessionExercise:
        for exercise in session.exercises:
            if exercise.id == session_exercise_id:
                return exercise
        raise HTTPException(status_code=404, detail="Session exercise not found")

    def _sync_aggregate_log(
        self,
        session: models.WorkoutSession,
        session_exercise: models.WorkoutSessionExercise,
    ) -> models.WorkoutLog:
        log = (
            self.db.query(models.WorkoutLog)
            .filter(
                models.WorkoutLog.session_id == session.id,
                models.WorkoutLog.planned_exercise_id == session_exercise.planned_exercise_id,
                models.WorkoutLog.exercise_name == session_exercise.exercise_name,
            )
            .first()
        )
        performed_sets = [item for item in session_exercise.sets if item.completed]
        completed = session_exercise.status != models.SessionExerciseStatus.skipped.value and bool(performed_sets)
        if log is None:
            log = models.WorkoutLog(
                user_id=session.user_id,
                session_id=session.id,
                planned_exercise_id=session_exercise.planned_exercise_id,
                exercise_name=session_exercise.exercise_name,
                performed_on=session.planned_for or date.today(),
                sets_completed=0,
                reps_completed=0,
                weight_kg=0,
                completed=completed,
                perceived_effort=7,
            )
            self.db.add(log)
            self.db.flush()
        log.performed_on = session.planned_for or date.today()
        log.sets_completed = len(performed_sets)
        log.reps_completed = sum(item.reps for item in performed_sets)
        log.weight_kg = max((item.weight_kg for item in performed_sets), default=0)
        log.completed = completed
        log.perceived_effort = max((item.perceived_effort for item in performed_sets), default=5)
        return log

    def _refresh_completion(self, session: models.WorkoutSession) -> None:
        total = len(session.exercises)
        if not total:
            session.completion_rate = 0
            return
        completed = sum(1 for item in session.exercises if item.status == models.SessionExerciseStatus.completed.value)
        session.completion_rate = completed / total

    def _readiness_dict(self, readiness: models.ReadinessCheckin | None) -> dict | None:
        if not readiness:
            return None
        return {
            "energy": readiness.energy,
            "sleep_quality": readiness.sleep_quality,
            "soreness": readiness.soreness,
            "stress": readiness.stress,
            "pain": readiness.pain,
            "pain_notes": readiness.pain_notes,
        }

    def _session_exercise_dict(self, exercise: models.WorkoutSessionExercise) -> dict:
        return {
            "id": exercise.id,
            "planned_exercise_id": exercise.planned_exercise_id,
            "exercise_id": exercise.exercise_id,
            "exercise_name": exercise.exercise_name,
            "order_index": exercise.order_index,
            "target_sets": exercise.target_sets,
            "target_reps": exercise.target_reps,
            "target_weight_kg": exercise.target_weight_kg,
            "status": exercise.status,
            "skip_reason": exercise.skip_reason,
            "notes": exercise.notes,
            "sets": [
                {
                    "id": item.id,
                    "set_number": item.set_number,
                    "reps": item.reps,
                    "weight_kg": item.weight_kg,
                    "perceived_effort": item.perceived_effort,
                    "completed": item.completed,
                    "pain_flag": item.pain_flag,
                    "notes": item.notes,
                }
                for item in sorted(exercise.sets, key=lambda performed_set: performed_set.set_number)
            ],
        }

    def _safety_notes(self, session: models.WorkoutSession) -> list[str]:
        notes: list[str] = []
        if session.readiness and session.readiness.pain is not None and session.readiness.pain >= 7:
            notes.append("High pain readiness check-in. Keep loads conservative and stop movements that aggravate pain.")
        if any(performed_set.pain_flag for exercise in session.exercises for performed_set in exercise.sets):
            notes.append("Pain was flagged during this session. Avoid increasing load for affected movements.")
        return notes
