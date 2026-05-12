import logging
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import get_settings
from app.db import get_db, init_db
from app.routes.analytics import router as analytics_router
from app.routes.audit import router as audit_router
from app.routes.business import router as business_router
from app.routes.notifications import router as notification_router
from app.routes.organizations import router as organization_router
from app.routes.sessions import router as session_router
from app.routes.trainer_workspace import router as trainer_workspace_router
from app.services.auth import account_dict, create_session, get_account_from_authorization, hash_password, normalize_email, revoke_session, verify_password
from app.services.demo_seed import DemoSeedService
from app.services.diet_planner import DietPlanner
from app.services.llm import LLMService
from app.services.review import WeeklyReviewService
from app.services.workout_planner import WorkoutPlanner

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend"
logger = logging.getLogger("fitgen.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()

app = FastAPI(title="FitGen AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(organization_router, prefix="/api")
app.include_router(trainer_workspace_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(business_router, prefix="/api")
app.include_router(notification_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(session_router, prefix="/api")


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed", extra={"request_id": request_id, "path": request.url.path})
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": exc.detail}, "request_id": getattr(request.state, "request_id", None)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Invalid request payload", "details": exc.errors()}, "request_id": getattr(request.state, "request_id", None)},
    )


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "FitGen AI"}


def _optional_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Account | None:
    return get_account_from_authorization(db, authorization)


def _require_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Account:
    account = get_account_from_authorization(db, authorization)
    if not account:
        raise HTTPException(status_code=401, detail="Authentication required")
    return account


@app.post("/api/auth/signup", response_model=schemas.AuthOut)
def signup(payload: schemas.AccountSignup, db: Session = Depends(get_db)) -> dict:
    email = normalize_email(payload.email)
    existing = db.query(models.Account).filter(models.Account.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Account already exists")

    account = models.Account(email=email, password_hash=hash_password(payload.password))
    db.add(account)
    db.flush()
    user = models.UserProfile(account_id=account.id, **payload.profile.model_dump())
    db.add(user)
    db.commit()
    db.refresh(account)
    db.refresh(user)
    WorkoutPlanner(db).generate_week(user)
    DietPlanner(db).generate_week(user)
    session = create_session(db, account)
    return {"token": session.token, "account": account_dict(account), "profile": _user_dict(user)}


@app.post("/api/auth/login", response_model=schemas.AuthOut)
def login(payload: schemas.AccountLogin, db: Session = Depends(get_db)) -> dict:
    account = db.query(models.Account).filter(models.Account.email == normalize_email(payload.email)).first()
    if not account or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    session = create_session(db, account)
    profile = db.query(models.UserProfile).filter(models.UserProfile.account_id == account.id).order_by(models.UserProfile.id).first()
    return {"token": session.token, "account": account_dict(account), "profile": _user_dict(profile) if profile else None}


@app.get("/api/auth/me", response_model=schemas.AuthOut)
def me(account: models.Account = Depends(_require_account), db: Session = Depends(get_db)) -> dict:
    profile = db.query(models.UserProfile).filter(models.UserProfile.account_id == account.id).order_by(models.UserProfile.id).first()
    return {"token": "", "account": account_dict(account), "profile": _user_dict(profile) if profile else None}


@app.post("/api/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    revoke_session(db, authorization)
    return {"status": "signed_out"}


@app.post("/api/users", response_model=schemas.UserProfileOut)
def create_user(
    payload: schemas.UserProfileCreate,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> models.UserProfile:
    user = models.UserProfile(account_id=account.id if account else None, **payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    WorkoutPlanner(db).generate_week(user)
    DietPlanner(db).generate_week(user)
    return user


@app.get("/api/users/{user_id}", response_model=schemas.UserProfileOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> models.UserProfile:
    return _get_user(db, user_id, account)


@app.get("/api/bootstrap")
def bootstrap(db: Session = Depends(get_db)) -> dict:
    if not settings.demo_routes_enabled:
        raise HTTPException(status_code=404, detail="Demo workspace is disabled")
    user = db.query(models.UserProfile).order_by(models.UserProfile.id).first()
    if not user:
        user = models.UserProfile(
            name="Aarav",
            age=29,
            height_cm=174,
            weight_kg=78,
            fitness_goal="fat_loss",
            diet_preference="non_veg",
            budget_amount=220,
            budget_period="daily",
            location="Pune, India",
            gym_type="local_gym",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        _seed_demo_history(db, user)
        WorkoutPlanner(db).generate_week(user)
        DietPlanner(db).generate_week(user)
        WeeklyReviewService(db).create_review(user)
    return dashboard(user.id, db, None)


@app.post("/api/demo/business")
def business_demo(db: Session = Depends(get_db)) -> dict:
    if not settings.demo_routes_enabled:
        raise HTTPException(status_code=404, detail="Demo workspace is disabled")
    return DemoSeedService(db).seed_business_demo()


@app.get("/api/users/{user_id}/dashboard", response_model=schemas.DashboardOut)
def dashboard(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    workout_planner = WorkoutPlanner(db)
    diet_planner = DietPlanner(db)
    review_service = WeeklyReviewService(db)
    plan = workout_planner.current_plan(user.id)
    diet = diet_planner.current_plan(user.id)
    review = review_service.latest_review(user.id)
    return {
        "user": _user_dict(user),
        "current_workout_plan": workout_planner.serialize_plan(plan),
        "current_diet_plan": diet_planner.serialize_plan(diet),
        "progress": _progress(db, user.id),
        "weekly_summary": review_service.serialize_review(review),
    }


@app.post("/api/users/{user_id}/plans/weekly")
def generate_weekly_plan(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    plan = WorkoutPlanner(db).generate_week(user)
    diet = DietPlanner(db).generate_week(user, plan.week_start)
    return {"workout_plan": WorkoutPlanner(db).serialize_plan(plan), "diet_plan": DietPlanner(db).serialize_plan(diet)}


@app.post("/api/users/{user_id}/ai/workout-proposal")
async def ai_workout_proposal(
    user_id: int,
    payload: schemas.AIWorkoutPlanRequest,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    planner = WorkoutPlanner(db)
    fallback = planner.generate_ai_ready_proposal(user, payload.equipment_text)
    proposal = await LLMService().workout_plan_proposal(
        {
            "profile": _user_dict(user),
            "progress": _progress(db, user.id),
            "equipment_summary": fallback["equipment_summary"],
            "fallback": fallback,
        }
    )
    return {"enabled": LLMService().is_enabled(), "proposal": proposal, "question": "Is this good enough to use for your week?"}


@app.post("/api/users/{user_id}/ai/workout-proposal/accept")
def accept_ai_workout_proposal(
    user_id: int,
    payload: schemas.AIWorkoutPlanProposal,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    planner = WorkoutPlanner(db)
    plan = planner.apply_plan_proposal(user, payload.model_dump())
    return {"status": "accepted", "workout_plan": planner.serialize_plan(plan)}


@app.post("/api/users/{user_id}/ai/exercise-advice")
async def ai_exercise_advice(
    user_id: int,
    payload: schemas.AIExerciseQuestionRequest,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    answer = await LLMService().exercise_answer(
        {
            "profile": _user_dict(user),
            "exercise_name": payload.exercise_name,
            "question": payload.question,
            "current_goal": user.fitness_goal,
            "fallback": (
                f"For {payload.exercise_name}, keep the load controlled, match the planned reps, "
                "and stop before form degrades. If the movement feels unstable, reduce load and clean up tempo first."
            ),
        }
    )
    return {"answer": answer}


@app.post("/api/users/{user_id}/ai/diet-analysis")
async def ai_diet_analysis(
    user_id: int,
    payload: schemas.AIDietAnalysisRequest,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    planner = DietPlanner(db)
    current = planner.current_plan(user.id)
    fallback = _diet_analysis_fallback(user, planner.serialize_plan(current), payload.foods_text)
    analysis = await LLMService().diet_analysis(
        {
            "profile": _user_dict(user),
            "question": payload.question,
            "foods_text": payload.foods_text,
            "current_targets": planner.serialize_plan(current),
            "fallback": fallback,
        }
    )
    return {"enabled": LLMService().is_enabled(), "analysis": analysis}


@app.get("/api/users/{user_id}/workouts/current")
def current_workout(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    planner = WorkoutPlanner(db)
    return {"workout_plan": planner.serialize_plan(planner.current_plan(user_id))}


@app.post("/api/users/{user_id}/workouts/logs")
def log_workout(
    user_id: int,
    payload: schemas.WorkoutLogCreate,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    _get_user(db, user_id, account)
    if payload.planned_exercise_id is not None:
        planned_exercise = db.get(models.WorkoutExercise, payload.planned_exercise_id)
        if not planned_exercise or planned_exercise.plan.user_id != user_id:
            raise HTTPException(status_code=400, detail="Planned exercise does not belong to this user")
    else:
        planned_exercise = None
    log = models.WorkoutLog(user_id=user_id, organization_id=user.organization_id, **payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"status": "logged", "log_id": log.id, "progress": _progress(db, user_id)}


@app.post("/api/users/{user_id}/feedback")
def submit_feedback(
    user_id: int,
    payload: schemas.FeedbackCreate,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    feedback = models.Feedback(user_id=user_id, organization_id=user.organization_id, signal=payload.signal, message=payload.message)
    db.add(feedback)
    db.commit()
    return {
        "status": "accepted",
        "effect": _feedback_effect(payload.signal),
        "next_step": "Generate next week's plan to apply this feedback.",
    }


@app.get("/api/users/{user_id}/diet/current")
def current_diet(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    _get_user(db, user_id, account)
    planner = DietPlanner(db)
    return {"diet_plan": planner.serialize_plan(planner.current_plan(user_id))}


@app.post("/api/users/{user_id}/weekly-review")
def create_weekly_review(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    review_service = WeeklyReviewService(db)
    return {"weekly_summary": review_service.serialize_review(review_service.create_review(user))}


@app.get("/api/users/{user_id}/report/export", response_class=PlainTextResponse)
def export_report(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> str:
    data = dashboard(user_id, db, account)
    review = data["weekly_summary"] or {}
    progress = data["progress"]
    diet = data["current_diet_plan"] or {}
    return "\n".join(
        [
            "FitGen AI Weekly Report",
            f"User: {data['user']['name']}",
            f"Goal: {data['user']['fitness_goal']}",
            f"Completion rate: {progress['completion_rate']:.0%}",
            f"Strength entries logged: {progress['total_logs']}",
            f"Diet target: {diet.get('calories', 'n/a')} kcal, {diet.get('protein_g', 'n/a')}g protein",
            f"Summary: {review.get('summary', 'No review yet')}",
            f"Adjustment: {review.get('adjustments', 'Run weekly review after logging sessions')}",
        ]
    )


def _get_user(db: Session, user_id: int, account: models.Account | None = None) -> models.UserProfile:
    user = db.get(models.UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.account_id is not None and (account is None or user.account_id != account.id):
        raise HTTPException(status_code=403, detail="Profile belongs to another account")
    return user


def _user_dict(user: models.UserProfile) -> dict:
    return {
        "id": user.id,
        "account_id": user.account_id,
        "organization_id": user.organization_id,
        "assigned_trainer_id": user.assigned_trainer_id,
        "member_code": user.member_code,
        "status": user.status,
        "joined_on": user.joined_on.isoformat() if user.joined_on else None,
        "name": user.name,
        "age": user.age,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "fitness_goal": user.fitness_goal,
        "diet_preference": user.diet_preference,
        "budget_amount": user.budget_amount,
        "budget_period": user.budget_period,
        "location": user.location,
        "gym_type": user.gym_type,
    }


def _progress(db: Session, user_id: int) -> dict:
    current_plan = (
        db.query(models.WorkoutPlan)
        .filter(models.WorkoutPlan.user_id == user_id)
        .order_by(desc(models.WorkoutPlan.week_start), desc(models.WorkoutPlan.id))
        .first()
    )
    logs = (
        db.query(models.WorkoutLog)
        .filter(models.WorkoutLog.user_id == user_id)
        .order_by(models.WorkoutLog.performed_on)
        .all()
    )
    total = len(logs)
    completed = sum(1 for log in logs if log.completed)
    planned_total = len(current_plan.exercises) if current_plan else 0
    planned_exercise_ids = {exercise.id for exercise in current_plan.exercises} if current_plan else set()
    latest_by_planned_exercise: dict[int, models.WorkoutLog] = {}
    for log in sorted(logs, key=lambda item: item.id, reverse=True):
        if log.planned_exercise_id is not None and log.planned_exercise_id in planned_exercise_ids and log.planned_exercise_id not in latest_by_planned_exercise:
            latest_by_planned_exercise[log.planned_exercise_id] = log
    planned_completed = len([log for log in latest_by_planned_exercise.values() if log.completed])
    planned_skipped = len([log for log in latest_by_planned_exercise.values() if not log.completed])
    by_exercise: dict[str, float] = {}
    chart = []
    for log in logs:
        by_exercise[log.exercise_name] = max(by_exercise.get(log.exercise_name, 0), log.weight_kg)
        chart.append(
            {
                "date": log.performed_on.isoformat(),
                "exercise": log.exercise_name,
                "volume": log.weight_kg * log.reps_completed,
                "effort": log.perceived_effort,
            }
        )
    return {
        "total_logs": total,
        "completion_rate": planned_completed / planned_total if planned_total else (completed / total if total else 0),
        "current_week_completed": planned_completed,
        "current_week_planned": planned_total,
        "current_week_skipped": planned_skipped,
        "best_weights": by_exercise,
        "chart": chart[-30:],
        "recent_logs": [
            {
                "planned_exercise_id": log.planned_exercise_id,
                "exercise": log.exercise_name,
                "date": log.performed_on.isoformat(),
                "sets": log.sets_completed,
                "reps": log.reps_completed,
                "weight_kg": log.weight_kg,
                "effort": log.perceived_effort,
                "completed": log.completed,
            }
            for log in reversed(logs[-8:])
        ],
    }


def _feedback_effect(signal: str) -> str:
    return {
        "too_hard": "Next plan reduces sets or load and keeps exercise selection stable.",
        "too_easy": "Next plan can apply progressive overload if completion rate stays high.",
        "missed_workout": "Next plan lowers volume and avoids aggressive load jumps.",
        "joint_pain": "Next plan should bias toward lower-impact alternatives.",
        "good": "Next plan keeps baseline progression.",
    }.get(signal, "Feedback stored for the next planning cycle.")


def _diet_analysis_fallback(user: models.UserProfile, current_plan: dict | None, foods_text: str) -> dict:
    foods = [item.strip() for item in foods_text.replace("\n", ",").split(",") if item.strip()]
    foods_lower = [item.lower() for item in foods]
    calories = current_plan["calories"] if current_plan else 0
    protein = current_plan["protein_g"] if current_plan else 0
    protein_hits = sum(1 for item in foods_lower if any(token in item for token in ["egg", "paneer", "dal", "chana", "soy", "milk", "curd", "chicken", "fish"]))
    carb_hits = sum(1 for item in foods_lower if any(token in item for token in ["rice", "roti", "poha", "oats", "bread", "dosa"]))
    fat_hits = sum(1 for item in foods_lower if any(token in item for token in ["peanut", "ghee", "oil", "butter", "nuts"]))
    estimated_calories = min(max(350, protein_hits * 180 + carb_hits * 220 + fat_hits * 130), max(600, calories))
    estimated_protein = min(max(18, protein_hits * 12), max(30, protein))
    benefits = []
    risks = []
    if protein_hits >= 2:
        benefits.append("You have enough protein anchors to support recovery if portions are consistent.")
    else:
        risks.append("Protein sources look thin, so recovery and satiety may suffer.")
    if carb_hits >= 1:
        benefits.append("There is enough easy carbohydrate to fuel training sessions.")
    else:
        risks.append("Very low training carbs can make sessions feel flat if volume rises.")
    if user.fitness_goal == "fat_loss":
        benefits.append("This food list can work for fat loss if portions stay measured and fried extras stay low.")
    if not risks:
        risks.append("The main tradeoff is portion control, because calorie drift usually comes from oils and snacks.")
    suggested_meals = [
        f"Meal 1: {foods[0] if foods else 'Dal'} + curd + one measured carb source",
        f"Meal 2: {foods[1] if len(foods) > 1 else 'Paneer or eggs'} + sabzi + roti/rice",
        "Meal 3: Keep one protein-focused snack around training",
    ]
    return {
        "summary": f"These foods can support {label_goal(user.fitness_goal)} if you keep protein regular and portion sizes honest.",
        "estimated_calories": int(estimated_calories),
        "estimated_protein_g": int(estimated_protein),
        "benefits": benefits,
        "risks": risks,
        "suggested_meals": suggested_meals,
    }


def label_goal(goal: str) -> str:
    return goal.replace("_", " ")


def _seed_demo_history(db: Session, user: models.UserProfile) -> None:
    start = date.today() - timedelta(days=13)
    demo = [
        ("Goblet Squat", 3, 34, 22.5, 8, True),
        ("Dumbbell Bench Press", 3, 30, 17.5, 8, True),
        ("One-arm Dumbbell Row", 3, 32, 20, 7, True),
        ("Romanian Deadlift", 3, 28, 45, 8, True),
        ("Goblet Squat", 2, 20, 20, 9, True),
        ("Dumbbell Bench Press", 0, 0, 0, 5, False),
        ("One-arm Dumbbell Row", 3, 36, 22.5, 7, True),
        ("Romanian Deadlift", 3, 30, 47.5, 8, True),
    ]
    for index, item in enumerate(demo):
        db.add(
            models.WorkoutLog(
                user_id=user.id,
                organization_id=user.organization_id,
                exercise_name=item[0],
                performed_on=start + timedelta(days=index + (index // 4) * 3),
                sets_completed=item[1],
                reps_completed=item[2],
                weight_kg=item[3],
                perceived_effort=item[4],
                completed=item[5],
            )
        )
    db.add(models.Feedback(user_id=user.id, organization_id=user.organization_id, signal="too_hard", message="Squats felt heavy after poor sleep."))
    db.commit()
