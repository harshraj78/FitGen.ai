from __future__ import annotations

import json
from typing import Any

from app.config import get_settings


class LLMService:
    """Optional LLM layer for proposal drafting and targeted coaching answers."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def is_enabled(self) -> bool:
        if self.settings.llm_provider == "groq":
            return bool(self.settings.groq_api_key)
        return bool(self.settings.openai_api_key)

    def _api_key(self) -> str | None:
        if self.settings.llm_provider == "groq":
            return self.settings.groq_api_key
        return self.settings.openai_api_key

    async def summarize_plan(self, context: dict) -> str:
        if not self.is_enabled():
            return context["fallback"]

        try:
            response = await self._chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are FitGen AI, a practical coach-engineer. "
                            "Use only the supplied metrics. Be concise and actionable."
                        ),
                    },
                    {"role": "user", "content": json.dumps(context)},
                ],
                temperature=0.2,
                max_tokens=180,
            )
            return response or context["fallback"]
        except Exception:
            return context["fallback"]

    async def workout_plan_proposal(self, payload: dict[str, Any]) -> dict[str, Any]:
        fallback = payload["fallback"]
        if not self.is_enabled():
            return fallback

        try:
            prompt = {
                "profile": payload["profile"],
                "progress": payload["progress"],
                "available_equipment": payload["equipment_summary"],
                "requirements": [
                    "Generate a realistic 6-day weekly plan matching the user's goal and gym context.",
                    "Use only equipment from available_equipment or bodyweight.",
                    "Keep notes practical and short.",
                    "Prefer exercises common in Indian gyms and home setups.",
                    "Return exactly 17 exercises spread across Mon-Sat.",
                ],
            }
            content = await self._structured_chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are FitGen AI. Build practical workout plans, not motivational copy. "
                            "Respect constraints. Use concise notes. Return only the requested schema."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt)},
                ],
                schema=self._workout_schema(),
                temperature=0.3,
                max_tokens=1400,
            )
            if not content:
                return fallback
            proposal = json.loads(content)
            if not self._valid_workout_proposal(proposal):
                return fallback
            return proposal
        except Exception:
            return fallback

    async def exercise_answer(self, payload: dict[str, Any]) -> str:
        if not self.is_enabled():
            return payload["fallback"]
        try:
            response = await self._chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are FitGen AI. Answer like a practical gym coach. "
                            "Stay specific to the named exercise and the user's goal. "
                            "Use 3-5 crisp sentences."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload)},
                ],
                temperature=0.3,
                max_tokens=220,
            )
            return response or payload["fallback"]
        except Exception:
            return payload["fallback"]

    async def diet_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        fallback = payload["fallback"]
        if not self.is_enabled():
            return fallback

        try:
            content = await self._structured_chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are FitGen AI. Analyze foods realistically for an India-friendly fitness plan. "
                            "Be practical about protein, calories, portions, and tradeoffs. Return only JSON."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload)},
                ],
                schema=self._diet_schema(),
                temperature=0.3,
                max_tokens=900,
            )
            if not content:
                return fallback
            analysis = json.loads(content)
            if not self._valid_diet_analysis(analysis):
                return fallback
            return analysis
        except Exception:
            return fallback

    async def _chat(self, messages: list[dict[str, str]], temperature: float, max_tokens: int) -> str | None:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key(), base_url=self.settings.llm_base_url)
        response = await client.chat.completions.create(
            model=self.settings.llm_model,
            messages=messages,
            temperature=max(temperature, 1e-8),
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def _structured_chat(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        temperature: float,
        max_tokens: int,
    ) -> str | None:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key(), base_url=self.settings.llm_base_url)
        response = await client.chat.completions.create(
            model=self.settings.llm_model,
            messages=messages,
            temperature=max(temperature, 1e-8),
            max_tokens=max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema["name"],
                    "strict": True,
                    "schema": schema["schema"],
                },
            },
        )
        return response.choices[0].message.content

    def _workout_schema(self) -> dict[str, Any]:
        return {
            "name": "fitgen_workout_plan",
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "rationale": {"type": "string"},
                    "equipment_summary": {"type": "array", "items": {"type": "string"}},
                    "days": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "day": {"type": "string"},
                                "focus": {"type": "string"},
                                "name": {"type": "string"},
                                "equipment": {"type": "string"},
                                "sets": {"type": "integer"},
                                "target_reps": {"type": "string"},
                                "target_weight_kg": {"type": "number"},
                                "notes": {"type": "string"},
                            },
                            "required": ["day", "focus", "name", "equipment", "sets", "target_reps", "target_weight_kg", "notes"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "rationale", "equipment_summary", "days"],
                "additionalProperties": False,
            },
        }

    def _diet_schema(self) -> dict[str, Any]:
        return {
            "name": "fitgen_diet_analysis",
            "schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "estimated_calories": {"type": "integer"},
                    "estimated_protein_g": {"type": "integer"},
                    "benefits": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "suggested_meals": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["summary", "estimated_calories", "estimated_protein_g", "benefits", "risks", "suggested_meals"],
                "additionalProperties": False,
            },
        }

    def _valid_workout_proposal(self, proposal: dict[str, Any]) -> bool:
        days = proposal.get("days")
        return isinstance(days, list) and len(days) >= 12 and all(isinstance(item, dict) for item in days)

    def _valid_diet_analysis(self, analysis: dict[str, Any]) -> bool:
        return all(key in analysis for key in ["summary", "estimated_calories", "estimated_protein_g", "benefits", "risks", "suggested_meals"])
