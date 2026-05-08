from datetime import date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class FitnessGoal(str, Enum):
    fat_loss = "fat_loss"
    muscle_gain = "muscle_gain"
    maintenance = "maintenance"


class DietPreference(str, Enum):
    veg = "veg"
    non_veg = "non_veg"


class GymType(str, Enum):
    home = "home"
    local_gym = "local_gym"
    premium_gym = "premium_gym"


class FeedbackSignal(str, Enum):
    too_hard = "too_hard"
    too_easy = "too_easy"
    missed_workout = "missed_workout"
    joint_pain = "joint_pain"
    good = "good"


class WorkoutSessionStatus(str, Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class SessionExerciseStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profiles: Mapped[list["UserProfile"]] = relationship(back_populates="account")
    sessions: Mapped[list["AccountSession"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class AccountSession(Base):
    __tablename__ = "account_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped[Account] = relationship(back_populates="sessions")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_user_profiles_account_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    fitness_goal: Mapped[str] = mapped_column(String(40), nullable=False)
    diet_preference: Mapped[str] = mapped_column(String(20), nullable=False)
    budget_amount: Mapped[float] = mapped_column(Float, nullable=False)
    budget_period: Mapped[str] = mapped_column(String(20), default="daily")
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    gym_type: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped[Account | None] = relationship(back_populates="profiles")
    workout_plans: Mapped[list["WorkoutPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    workout_logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    diet_plans: Mapped[list["DietPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    weekly_reviews: Mapped[list["WeeklyReview"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    workout_sessions: Mapped[list["WorkoutSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    intensity_modifier: Mapped[float] = mapped_column(Float, default=1.0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[UserProfile] = relationship(back_populates="workout_plans")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("workout_plans.id"), index=True)
    exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"), nullable=True, index=True)
    day_index: Mapped[int] = mapped_column(Integer, nullable=False)
    day_name: Mapped[str] = mapped_column(String(20), nullable=False)
    focus: Mapped[str] = mapped_column(String(80), nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(140), nullable=False)
    equipment: Mapped[str] = mapped_column(String(80), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps: Mapped[str] = mapped_column(String(40), nullable=False)
    target_weight_kg: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    plan: Mapped[WorkoutPlan] = relationship(back_populates="exercises")
    exercise: Mapped["Exercise | None"] = relationship()


class WorkoutLog(Base):
    __tablename__ = "workout_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    planned_exercise_id: Mapped[int | None] = mapped_column(ForeignKey("workout_exercises.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("workout_sessions.id"), nullable=True, index=True)
    exercise_name: Mapped[str] = mapped_column(String(140), nullable=False)
    performed_on: Mapped[date] = mapped_column(Date, nullable=False)
    sets_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    reps_completed: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    completed: Mapped[bool] = mapped_column(default=True)
    perceived_effort: Mapped[int] = mapped_column(Integer, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[UserProfile] = relationship(back_populates="workout_logs")
    planned_exercise: Mapped["WorkoutExercise | None"] = relationship()
    session: Mapped["WorkoutSession | None"] = relationship(back_populates="workout_logs")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    signal: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[UserProfile] = relationship(back_populates="feedback")


class DietPlan(Base):
    __tablename__ = "diet_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_daily_cost: Mapped[float] = mapped_column(Float, nullable=False)
    meals_json: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[UserProfile] = relationship(back_populates="diet_plans")


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, default=0)
    strength_delta: Mapped[float] = mapped_column(Float, default=0)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    adjustments: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[UserProfile] = relationship(back_populates="weekly_reviews")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    focus: Mapped[str] = mapped_column(String(80), nullable=False)
    movement_pattern: Mapped[str] = mapped_column(String(80), nullable=False)
    equipment: Mapped[str] = mapped_column(String(80), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(40), default="beginner")
    primary_muscles: Mapped[str] = mapped_column(String(200), default="")
    joint_stress_tags: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    aliases: Mapped[list["ExerciseAlias"]] = relationship(back_populates="exercise", cascade="all, delete-orphan")


class ExerciseAlias(Base):
    __tablename__ = "exercise_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    alias: Mapped[str] = mapped_column(String(140), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    exercise: Mapped[Exercise] = relationship(back_populates="aliases")


class ExerciseSubstitution(Base):
    __tablename__ = "exercise_substitutions"
    __table_args__ = (UniqueConstraint("source_exercise_id", "substitute_exercise_id", name="uq_exercise_substitution_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    substitute_exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    reason: Mapped[str] = mapped_column(String(120), default="equipment_fallback")
    equipment_constraint: Mapped[str] = mapped_column(String(80), default="")
    pain_constraint: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    source_exercise: Mapped[Exercise] = relationship(foreign_keys=[source_exercise_id])
    substitute_exercise: Mapped[Exercise] = relationship(foreign_keys=[substitute_exercise_id])


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    workout_plan_id: Mapped[int | None] = mapped_column(ForeignKey("workout_plans.id"), nullable=True, index=True)
    day_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=WorkoutSessionStatus.active.value, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    session_rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    completion_rate: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[UserProfile] = relationship(back_populates="workout_sessions")
    plan: Mapped["WorkoutPlan | None"] = relationship()
    readiness: Mapped["ReadinessCheckin | None"] = relationship(back_populates="session", cascade="all, delete-orphan")
    exercises: Mapped[list["WorkoutSessionExercise"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    workout_logs: Mapped[list["WorkoutLog"]] = relationship(back_populates="session")


class ReadinessCheckin(Base):
    __tablename__ = "readiness_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    energy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soreness: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[WorkoutSession] = relationship(back_populates="readiness")


class WorkoutSessionExercise(Base):
    __tablename__ = "workout_session_exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("workout_sessions.id"), index=True)
    planned_exercise_id: Mapped[int | None] = mapped_column(ForeignKey("workout_exercises.id"), nullable=True, index=True)
    exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id"), nullable=True, index=True)
    exercise_name: Mapped[str] = mapped_column(String(140), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    target_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    target_reps: Mapped[str] = mapped_column(String(40), nullable=False)
    target_weight_kg: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(30), default=SessionExerciseStatus.pending.value, index=True)
    skip_reason: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped[WorkoutSession] = relationship(back_populates="exercises")
    planned_exercise: Mapped["WorkoutExercise | None"] = relationship()
    exercise: Mapped["Exercise | None"] = relationship()
    sets: Mapped[list["PerformedSet"]] = relationship(back_populates="session_exercise", cascade="all, delete-orphan")


class PerformedSet(Base):
    __tablename__ = "performed_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_exercise_id: Mapped[int] = mapped_column(ForeignKey("workout_session_exercises.id"), index=True)
    workout_log_id: Mapped[int | None] = mapped_column(ForeignKey("workout_logs.id"), nullable=True, index=True)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    perceived_effort: Mapped[int] = mapped_column(Integer, default=7)
    completed: Mapped[bool] = mapped_column(default=True)
    pain_flag: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session_exercise: Mapped[WorkoutSessionExercise] = relationship(back_populates="sets")
    workout_log: Mapped["WorkoutLog | None"] = relationship()
