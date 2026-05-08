from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.db import get_db
from app.services.auth import get_account_from_authorization
from app.services.session_service import WorkoutSessionService


router = APIRouter()


def _optional_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Account | None:
    return get_account_from_authorization(db, authorization)


def _get_user(db: Session, user_id: int, account: models.Account | None = None) -> models.UserProfile:
    user = db.get(models.UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.account_id is not None and (account is None or user.account_id != account.id):
        raise HTTPException(status_code=403, detail="Profile belongs to another account")
    return user


@router.post("/users/{user_id}/sessions/start")
def start_session(
    user_id: int,
    payload: schemas.WorkoutSessionStart,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    user = _get_user(db, user_id, account)
    service = WorkoutSessionService(db)
    session = service.start_session(user, payload)
    return {"session": service.serialize_session(session)}


@router.get("/users/{user_id}/sessions/active")
def active_session(
    user_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    _get_user(db, user_id, account)
    service = WorkoutSessionService(db)
    return {"session": service.serialize_session(service.get_active_session(user_id))}


@router.get("/sessions/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    session = WorkoutSessionService(db).get_session(session_id)
    _get_user(db, session.user_id, account)
    return {"session": WorkoutSessionService(db).serialize_session(session)}


@router.post("/sessions/{session_id}/exercises/{session_exercise_id}/sets")
def log_set(
    session_id: int,
    session_exercise_id: int,
    payload: schemas.PerformedSetCreate,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    service = WorkoutSessionService(db)
    session = service.get_session(session_id)
    _get_user(db, session.user_id, account)
    updated = service.log_set(session, session_exercise_id, payload)
    return {"session": service.serialize_session(updated)}


@router.post("/sessions/{session_id}/exercises/{session_exercise_id}/skip")
def skip_exercise(
    session_id: int,
    session_exercise_id: int,
    payload: schemas.SessionExerciseSkip,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    service = WorkoutSessionService(db)
    session = service.get_session(session_id)
    _get_user(db, session.user_id, account)
    updated = service.skip_exercise(session, session_exercise_id, payload)
    return {"session": service.serialize_session(updated)}


@router.post("/sessions/{session_id}/finish")
def finish_session(
    session_id: int,
    payload: schemas.WorkoutSessionFinish,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    service = WorkoutSessionService(db)
    session = service.get_session(session_id)
    _get_user(db, session.user_id, account)
    updated = service.finish_session(session, payload)
    return {"session": service.serialize_session(updated)}


@router.post("/sessions/{session_id}/abandon")
def abandon_session(
    session_id: int,
    db: Session = Depends(get_db),
    account: models.Account | None = Depends(_optional_account),
) -> dict:
    service = WorkoutSessionService(db)
    session = service.get_session(session_id)
    _get_user(db, session.user_id, account)
    updated = service.abandon_session(session)
    return {"session": service.serialize_session(updated)}
