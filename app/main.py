from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db, init_db
from app.services.diet_planner import DietPlanner
from app.services.review import WeeklyReviewService
from app.services.workout_planner import WorkoutPlanner

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "frontend"

app = FastAPI(title="FitGen AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "FitGen AI"}


@app.post("/api/users", response_model=schemas.UserProfileOut)
def create_user(payload: schemas.UserProfileCreate, db: Session = Depends(get_db)) -> models.UserProfile:
    user = models.UserProfile(**payload.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    WorkoutPlanner(db).generate_week(user)
    DietPlanner(db).generate_week(user)
    return user


@app.get("/api/users/{user_id}", response_model=schemas.UserProfileOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> models.UserProfile:
    return _get_user(db, user_id)


@app.get("/api/bootstrap")
def bootstrap(db: Session = Depends(get_db)) -> dict:
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
    return dashboard(user.id, db)


@app.get("/api/users/{user_id}/dashboard", response_model=schemas.DashboardOut)
def dashboard(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = _get_user(db, user_id)
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
def generate_weekly_plan(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = _get_user(db, user_id)
    plan = WorkoutPlanner(db).generate_week(user)
    diet = DietPlanner(db).generate_week(user, plan.week_start)
    return {"workout_plan": WorkoutPlanner(db).serialize_plan(plan), "diet_plan": DietPlanner(db).serialize_plan(diet)}


@app.get("/api/users/{user_id}/workouts/current")
def current_workout(user_id: int, db: Session = Depends(get_db)) -> dict:
    _get_user(db, user_id)
    planner = WorkoutPlanner(db)
    return {"workout_plan": planner.serialize_plan(planner.current_plan(user_id))}


@app.post("/api/users/{user_id}/workouts/logs")
def log_workout(user_id: int, payload: schemas.WorkoutLogCreate, db: Session = Depends(get_db)) -> dict:
    _get_user(db, user_id)
    log = models.WorkoutLog(user_id=user_id, **payload.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"status": "logged", "log_id": log.id, "progress": _progress(db, user_id)}


@app.post("/api/users/{user_id}/feedback")
def submit_feedback(user_id: int, payload: schemas.FeedbackCreate, db: Session = Depends(get_db)) -> dict:
    _get_user(db, user_id)
    feedback = models.Feedback(user_id=user_id, signal=payload.signal, message=payload.message)
    db.add(feedback)
    db.commit()
    return {
        "status": "accepted",
        "effect": _feedback_effect(payload.signal),
        "next_step": "Generate next week's plan to apply this feedback.",
    }


@app.get("/api/users/{user_id}/diet/current")
def current_diet(user_id: int, db: Session = Depends(get_db)) -> dict:
    _get_user(db, user_id)
    planner = DietPlanner(db)
    return {"diet_plan": planner.serialize_plan(planner.current_plan(user_id))}


@app.post("/api/users/{user_id}/weekly-review")
def create_weekly_review(user_id: int, db: Session = Depends(get_db)) -> dict:
    user = _get_user(db, user_id)
    review_service = WeeklyReviewService(db)
    return {"weekly_summary": review_service.serialize_review(review_service.create_review(user))}


@app.get("/api/users/{user_id}/report/export", response_class=PlainTextResponse)
def export_report(user_id: int, db: Session = Depends(get_db)) -> str:
    data = dashboard(user_id, db)
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


def _get_user(db: Session, user_id: int) -> models.UserProfile:
    user = db.get(models.UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _user_dict(user: models.UserProfile) -> dict:
    return {
        "id": user.id,
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
    logs = (
        db.query(models.WorkoutLog)
        .filter(models.WorkoutLog.user_id == user_id)
        .order_by(models.WorkoutLog.performed_on)
        .all()
    )
    total = len(logs)
    completed = sum(1 for log in logs if log.completed)
    by_exercise: dict[str, float] = {}
    chart = []
    for log in logs:
        by_exercise[log.exercise_name] = max(by_exercise.get(log.exercise_name, 0), log.weight_kg)
        chart.append(
            {
                "date": log.performed_on.isoformat(),
                "exercise": log.exercise_name,
                "volume": log.weight_kg * log.reps_completed * max(log.sets_completed, 1),
                "effort": log.perceived_effort,
            }
        )
    return {
        "total_logs": total,
        "completion_rate": completed / total if total else 0,
        "best_weights": by_exercise,
        "chart": chart[-30:],
        "recent_logs": [
            {
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
                exercise_name=item[0],
                performed_on=start + timedelta(days=index + (index // 4) * 3),
                sets_completed=item[1],
                reps_completed=item[2],
                weight_kg=item[3],
                perceived_effort=item[4],
                completed=item[5],
            )
        )
    db.add(models.Feedback(user_id=user.id, signal="too_hard", message="Squats felt heavy after poor sleep."))
    db.commit()
