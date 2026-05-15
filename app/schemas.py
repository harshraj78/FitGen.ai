from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    data: T
    request_id: str | None = None


class PageMeta(BaseModel):
    limit: int
    offset: int
    total: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


class UserProfileCreate(BaseModel):
    name: str
    phone: str = Field(default="", max_length=40)
    email: str = Field(default="", max_length=255)
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


class MemberMiniOut(BaseModel):
    id: int
    account_id: int | None = None
    organization_id: int | None = None
    assigned_trainer_id: int | None = None
    member_code: str
    phone: str = ""
    email: str = ""
    status: str
    name: str
    age: int
    fitness_goal: str
    gym_type: str
    joined_on: date | None = None

    model_config = {"from_attributes": True}


class AdherenceMetrics(BaseModel):
    planned_sessions: int
    completed_sessions: int
    missed_sessions: int
    adherence_rate: float
    workout_logs_30d: int
    last_workout_on: date | None = None


class ReadinessFatigueSummary(BaseModel):
    checkins_14d: int
    average_energy: float | None = None
    average_soreness: float | None = None
    average_stress: float | None = None
    average_pain: float | None = None
    high_fatigue: bool


class MembershipSummary(BaseModel):
    status: str | None = None
    plan_name: str | None = None
    ends_on: date | None = None
    days_remaining: int | None = None


class LatestWorkoutSummary(BaseModel):
    session_id: int | None = None
    workout_plan_id: int | None = None
    performed_on: date | None = None
    status: str | None = None
    completion_rate: float | None = None


class RiskSignal(BaseModel):
    code: str
    severity: str
    message: str


class TrainerClientSummary(BaseModel):
    member: MemberMiniOut
    active_goals: list[GoalOut]
    adherence: AdherenceMetrics
    latest_workout: LatestWorkoutSummary
    readiness: ReadinessFatigueSummary
    membership: MembershipSummary
    risk_signals: list[RiskSignal]


class PendingPlanApproval(BaseModel):
    plan_id: int
    member: MemberMiniOut
    title: str
    week_start: date
    status: str
    created_at: datetime
    rationale: str


class MemberAnalyticsOut(BaseModel):
    member_id: int
    workout_consistency: AdherenceMetrics
    attendance_rate: float
    goal_completion_pct: float
    volume_progression: list[dict[str, Any]]
    readiness: ReadinessFatigueSummary


class TrainerAnalyticsOut(BaseModel):
    trainer_account_id: int
    assigned_clients: int
    at_risk_clients: int
    pending_plan_reviews: int
    average_adherence_rate: float
    overdue_goals: int


class GymAnalyticsOut(BaseModel):
    organization_id: int
    active_members: int
    active_memberships: int
    monthly_revenue: float
    overdue_revenue: float
    attendance_30d: int
    goal_completion_pct: float
    membership_renewals_30d: int
    trainer_performance: list[TrainerAnalyticsOut]


class RenewalRiskSignal(BaseModel):
    code: str
    severity: str
    message: str
    contribution: float


class RenewalRiskOut(BaseModel):
    member: MemberMiniOut
    membership: MembershipSummary
    score: float
    level: str
    signals: list[RenewalRiskSignal]
    forecast_renewal_on: date | None = None
    revenue_at_risk: float
    generated_at: datetime | None = None


class RenewalForecastOut(BaseModel):
    organization_id: int
    window_days: int
    expiring_memberships: int
    high_risk_renewals: int
    forecast_revenue: float
    revenue_at_risk: float
    expected_renewals: int
    renewal_probability: float
    at_risk_members: list[RenewalRiskOut]


class RevenueTrendPoint(BaseModel):
    period: str
    revenue: float = 0
    renewals: int = 0
    expired: int = 0
    churned: int = 0


class UnpaidMemberOut(BaseModel):
    member: MemberMiniOut
    amount_due: float
    oldest_due_on: date | None = None
    overdue_payments: int


class RevenueOperationsOut(BaseModel):
    organization_id: int
    monthly_recurring_revenue: float
    active_memberships: int
    expiring_memberships_30d: int
    unpaid_members: list[UnpaidMemberOut]
    overdue_revenue: float
    renewal_trends: list[RevenueTrendPoint]
    retention_trends: list[RevenueTrendPoint]
    churn_risk_summary: dict[str, int]


class TrainerPerformanceOut(BaseModel):
    trainer_account_id: int
    trainer_email: str | None = None
    active_client_count: int
    client_retention_rate: float
    avg_client_adherence: float
    goal_success_rate: float
    consistency_trend: float
    overdue_approvals: int
    inactive_clients: int
    high_risk_clients: int


class TrainerPerformanceComparisonOut(BaseModel):
    organization_id: int
    trainers: list[TrainerPerformanceOut]


class RetentionWorkflowOut(BaseModel):
    id: int | None = None
    organization_id: int
    member: MemberMiniOut
    assigned_account_id: int | None = None
    workflow_type: str
    status: str = "open"
    priority: str
    title: str
    message: str
    due_on: date | None = None
    source_entity_type: str = ""
    source_entity_id: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class OperationalDailyActionsOut(BaseModel):
    organization_id: int
    actions: list[RetentionWorkflowOut]
    summary: dict[str, int]


class BodyMetricSnapshotCreate(BaseModel):
    measured_on: date
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    body_fat_pct: float | None = Field(default=None, ge=1, le=80)
    waist_cm: float | None = Field(default=None, ge=30, le=250)
    chest_cm: float | None = Field(default=None, ge=30, le=250)
    hip_cm: float | None = Field(default=None, ge=30, le=250)
    notes: str = Field(default="", max_length=2000)


class BodyMetricSnapshotOut(BodyMetricSnapshotCreate):
    id: int
    organization_id: int
    member_id: int
    recorded_by_account_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransformationMilestoneCreate(BaseModel):
    milestone_type: str = Field(min_length=2, max_length=60)
    title: str = Field(min_length=2, max_length=180)
    achieved_on: date
    value: float | None = None
    unit: str = Field(default="", max_length=40)
    notes: str = Field(default="", max_length=2000)


class TransformationMilestoneOut(TransformationMilestoneCreate):
    id: int
    organization_id: int
    member_id: int
    trainer_account_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransformationSummaryOut(BaseModel):
    member: MemberMiniOut
    body_metric_improvements: dict[str, float | None]
    strength_progression: list[dict[str, Any]]
    consistency_improvement: float
    goal_completion_history: list[dict[str, Any]]
    milestones: list[TransformationMilestoneOut]


class TrainerTransformationOut(BaseModel):
    trainer_account_id: int
    active_clients: int
    clients_with_improvements: int
    avg_consistency_improvement: float
    goal_success_rate: float
    milestones_90d: int


class GymTransformationOut(BaseModel):
    organization_id: int
    members_tracked: int
    members_with_body_improvements: int
    avg_consistency_improvement: float
    goal_completion_pct: float
    milestones_90d: int
    trainer_success: list[TrainerTransformationOut]


class BusinessDashboardOut(BaseModel):
    organization_id: int
    revenue: RevenueOperationsOut
    renewal_forecast: RenewalForecastOut
    trainer_performance: list[TrainerPerformanceOut]
    daily_actions: OperationalDailyActionsOut
    at_risk_members: list[RenewalRiskOut]


class NotificationOut(BaseModel):
    id: int
    organization_id: int | None = None
    recipient_account_id: int | None = None
    recipient_user_id: int | None = None
    event_type: str
    channel: str
    title: str
    message: str
    read_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    event_type: str
    channel: str = "in_app"
    enabled: bool


class AIExplainabilityOut(BaseModel):
    id: int
    organization_id: int | None = None
    user_id: int
    workout_plan_id: int | None = None
    entity_type: str
    entity_id: int | None = None
    reason_code: str
    message: str
    metadata: dict[str, Any]
    created_at: datetime


class AuditLogOut(BaseModel):
    id: int
    organization_id: int | None = None
    actor_account_id: int | None = None
    actor_user_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    metadata: dict[str, Any]
    created_at: datetime


class DashboardOut(BaseModel):
    user: dict[str, Any]
    current_workout_plan: dict[str, Any] | None
    current_diet_plan: dict[str, Any] | None
    progress: dict[str, Any]
    weekly_summary: dict[str, Any] | None
