from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class UserProfileCreate(BaseModel):
    name: str
    age: int = Field(ge=13, le=90)
    height_cm: float = Field(gt=100, lt=230)
    weight_kg: float = Field(gt=30, lt=250)
    fitness_goal: str
    diet_preference: str
    budget_amount: float = Field(gt=0)
    budget_period: str = "daily"
    location: str
    gym_type: str


class UserProfileOut(UserProfileCreate):
    id: int
    account_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountSignup(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    profile: UserProfileCreate


class AccountLogin(BaseModel):
    email: str
    password: str


class AuthOut(BaseModel):
    token: str
    account: dict[str, Any]
    profile: dict[str, Any] | None = None


class WorkoutLogCreate(BaseModel):
    planned_exercise_id: int | None = None
    exercise_name: str
    performed_on: date
    sets_completed: int = Field(ge=0, le=20)
    reps_completed: int = Field(ge=0, le=300)
    weight_kg: float = Field(ge=0, le=500)
    completed: bool = True
    perceived_effort: int = Field(default=7, ge=1, le=10)


class FeedbackCreate(BaseModel):
    signal: str
    message: str = ""


class AIWorkoutPlanRequest(BaseModel):
    equipment_text: str = Field(min_length=2, max_length=3000)


class AIExerciseQuestionRequest(BaseModel):
    exercise_name: str
    question: str = Field(min_length=3, max_length=2000)


class AIDietAnalysisRequest(BaseModel):
    foods_text: str = Field(min_length=2, max_length=3000)
    question: str = Field(default="How can I use these foods well this week?", max_length=2000)


class AIPlanExercise(BaseModel):
    day: str
    focus: str
    name: str
    equipment: str
    sets: int = Field(ge=1, le=8)
    target_reps: str
    target_weight_kg: float = Field(ge=0, le=500)
    notes: str


class AIWorkoutPlanProposal(BaseModel):
    title: str
    rationale: str
    equipment_summary: list[str]
    days: list[AIPlanExercise]


class DashboardOut(BaseModel):
    user: dict[str, Any]
    current_workout_plan: dict[str, Any] | None
    current_diet_plan: dict[str, Any] | None
    progress: dict[str, Any]
    weekly_summary: dict[str, Any] | None
