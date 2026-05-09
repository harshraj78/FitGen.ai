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
    member_code: str = ""
    assigned_trainer_id: int | None = None


class UserProfileOut(UserProfileCreate):
    id: int
    account_id: int | None = None
    organization_id: int | None = None
    status: str = "active"
    joined_on: date | None = None
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


class ReadinessCheckinCreate(BaseModel):
    energy: int | None = Field(default=None, ge=1, le=10)
    sleep_quality: int | None = Field(default=None, ge=1, le=10)
    soreness: int | None = Field(default=None, ge=1, le=10)
    stress: int | None = Field(default=None, ge=1, le=10)
    pain: int | None = Field(default=None, ge=0, le=10)
    pain_notes: str = Field(default="", max_length=1000)


class WorkoutSessionStart(BaseModel):
    workout_plan_id: int | None = None
    day_index: int | None = Field(default=None, ge=1, le=7)
    planned_for: date | None = None
    readiness: ReadinessCheckinCreate | None = None


class PerformedSetCreate(BaseModel):
    reps: int = Field(ge=0, le=100)
    weight_kg: float = Field(ge=0, le=500)
    perceived_effort: int = Field(default=7, ge=1, le=10)
    completed: bool = True
    pain_flag: bool = False
    notes: str = Field(default="", max_length=1000)


class SessionExerciseSkip(BaseModel):
    reason: str = Field(default="other", max_length=80)
    notes: str = Field(default="", max_length=1000)


class WorkoutSessionFinish(BaseModel):
    session_rpe: int | None = Field(default=None, ge=1, le=10)
    notes: str = Field(default="", max_length=2000)


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


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=120)
    legal_name: str = Field(default="", max_length=200)
    timezone: str = Field(default="Asia/Kolkata", max_length=80)
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=2000)


class OrganizationOut(BaseModel):
    id: int
    name: str
    slug: str
    legal_name: str
    status: str
    timezone: str
    phone: str
    email: str
    address: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationMembershipCreate(BaseModel):
    account_id: int
    role: str


class OrganizationMembershipOut(BaseModel):
    id: int
    organization_id: int
    account_id: int
    role: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationMemberCreate(UserProfileCreate):
    account_id: int | None = None
    status: str = "active"
    joined_on: date | None = None


class MembershipPlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    duration_days: int = Field(ge=1, le=3700)
    price_amount: float = Field(ge=0)
    currency: str = Field(default="INR", max_length=12)
    description: str = Field(default="", max_length=2000)


class MembershipPlanOut(MembershipPlanCreate):
    id: int
    organization_id: int
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MemberMembershipCreate(BaseModel):
    plan_id: int | None = None
    starts_on: date
    ends_on: date
    status: str = "active"
    notes: str = Field(default="", max_length=2000)


class MemberMembershipOut(MemberMembershipCreate):
    id: int
    organization_id: int
    member_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    membership_id: int | None = None
    amount: float = Field(gt=0)
    currency: str = Field(default="INR", max_length=12)
    status: str = "pending"
    due_on: date | None = None
    paid_on: date | None = None
    method: str = Field(default="", max_length=40)
    reference: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=2000)


class PaymentOut(PaymentCreate):
    id: int
    organization_id: int
    member_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceCheckinCreate(BaseModel):
    method: str = "manual"
    notes: str = Field(default="", max_length=1000)


class AttendanceCheckinOut(BaseModel):
    id: int
    organization_id: int
    member_id: int
    checked_in_at: datetime
    method: str
    recorded_by_account_id: int | None = None
    notes: str

    model_config = {"from_attributes": True}


class GoalCreate(BaseModel):
    goal_type: str = "custom"
    title: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=3000)
    target_value: float | None = None
    current_value: float | None = None
    unit: str = Field(default="", max_length=40)
    starts_on: date | None = None
    target_date: date | None = None
    assigned_trainer_id: int | None = None


class GoalProgressUpdate(BaseModel):
    current_value: float | None = None
    status: str | None = None


class GoalOut(GoalCreate):
    id: int
    organization_id: int | None = None
    member_id: int
    created_by_account_id: int | None = None
    status: str
    achieved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    progress_pct: float | None = None
    projected_completion: date | None = None

    model_config = {"from_attributes": True}


class WorkoutPlanReview(BaseModel):
    status: str = Field(pattern="^(trainer_approved|trainer_modified)$")
    trainer_notes: str = Field(default="", max_length=4000)


class DashboardOut(BaseModel):
    user: dict[str, Any]
    current_workout_plan: dict[str, Any] | None
    current_diet_plan: dict[str, Any] | None
    progress: dict[str, Any]
    weekly_summary: dict[str, Any] | None
