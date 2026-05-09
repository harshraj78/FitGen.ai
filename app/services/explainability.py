from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app import models


class ExplainabilityService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        user: models.UserProfile,
        reason_code: str,
        message: str,
        entity_type: str,
        entity_id: int | None = None,
        workout_plan_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> models.AIExplainabilityRecord:
        record = models.AIExplainabilityRecord(
            organization_id=user.organization_id,
            user_id=user.id,
            workout_plan_id=workout_plan_id,
            entity_type=entity_type,
            entity_id=entity_id,
            reason_code=reason_code,
            message=message,
            metadata_json=json.dumps(metadata or {}, sort_keys=True),
        )
        self.db.add(record)
        return record

    def deterministic_reasons(self, user: models.UserProfile, metrics: dict[str, Any], modifier: float) -> list[dict[str, Any]]:
        reasons: list[dict[str, Any]] = []
        recent_feedback = metrics.get("recent_feedback", [])
        if modifier < 0.95:
            code = "fatigue_high" if "too_hard" in recent_feedback[:3] else "adherence_low"
            message = (
                "Reduced training intensity due to recent high-effort or fatigue feedback."
                if code == "fatigue_high"
                else "Reduced weekly volume because recent completion dropped."
            )
            reasons.append({"reason_code": code, "message": message, "metadata": {"modifier": modifier}})
        if "joint_pain" in recent_feedback[:5]:
            reasons.append(
                {
                    "reason_code": "pain_reported",
                    "message": "Exercise selection should prefer lower-joint-stress substitutions because pain was reported recently.",
                    "metadata": {"recent_feedback": recent_feedback[:5]},
                }
            )
        if user.organization_id and user.assigned_trainer_id:
            reasons.append(
                {
                    "reason_code": "trainer_review_required",
                    "message": "Plan requires trainer review before the member receives an authorized version.",
                    "metadata": {"assigned_trainer_id": user.assigned_trainer_id},
                }
            )
        return reasons

    def serialize(self, record: models.AIExplainabilityRecord) -> dict[str, Any]:
        try:
            metadata = json.loads(record.metadata_json or "{}")
        except json.JSONDecodeError:
            metadata = {}
        return {
            "id": record.id,
            "organization_id": record.organization_id,
            "user_id": record.user_id,
            "workout_plan_id": record.workout_plan_id,
            "entity_type": record.entity_type,
            "entity_id": record.entity_id,
            "reason_code": record.reason_code,
            "message": record.message,
            "metadata": metadata if isinstance(metadata, dict) else {},
            "created_at": record.created_at,
        }
