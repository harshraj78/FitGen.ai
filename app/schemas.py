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
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkoutLogCreate(BaseModel):
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


class DashboardOut(BaseModel):
    user: dict[str, Any]
    current_workout_plan: dict[str, Any] | None
    current_diet_plan: dict[str, Any] | None
    progress: dict[str, Any]
    weekly_summary: dict[str, Any] | None
