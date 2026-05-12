from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.db import get_db


HASH_ITERATIONS = 260_000


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, HASH_ITERATIONS)
    return f"pbkdf2_sha256${HASH_ITERATIONS}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, digest = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _unb64(salt),
            int(iterations),
        )
        return hmac.compare_digest(_b64(candidate), digest)
    except (ValueError, TypeError):
        return False


def create_session(db: Session, account: models.Account) -> models.AccountSession:
    session = models.AccountSession(account_id=account.id, token=secrets.token_urlsafe(48))
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_account_from_authorization(db: Session, authorization: str | None) -> models.Account | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    session = db.query(models.AccountSession).filter(models.AccountSession.token == token).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if _session_expired(session):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session.account


def revoke_session(db: Session, authorization: str | None) -> None:
    if not authorization:
        return
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return
    session = db.query(models.AccountSession).filter(models.AccountSession.token == token).first()
    if session:
        db.delete(session)
        db.commit()


def require_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.Account:
    account = get_account_from_authorization(db, authorization)
    if not account:
        raise HTTPException(status_code=401, detail="Authentication required")
    return account


def account_dict(account: models.Account) -> dict:
    return {"id": account.id, "email": account.email, "created_at": account.created_at.isoformat()}


def _session_expired(session: models.AccountSession) -> bool:
    ttl_hours = max(1, get_settings().session_ttl_hours)
    created_at = session.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created_at > timedelta(hours=ttl_hours)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))
