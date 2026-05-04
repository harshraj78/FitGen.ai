from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models


LOCAL_FOOD_BANK = {
    "north": ["roti", "dal", "curd", "paneer", "chana", "rajma", "eggs", "seasonal sabzi"],
    "south": ["rice", "sambar", "curd rice", "eggs", "fish", "dosa", "sprouts", "peanut chutney"],
    "west": ["roti", "dal", "poha", "eggs", "paneer", "curd", "peanuts", "seasonal sabzi"],
    "east": ["rice", "dal", "eggs", "fish", "chana", "curd", "seasonal greens"],
    "default": ["dal", "roti", "rice", "eggs", "paneer", "curd", "chana", "seasonal sabzi"],
}


class DietPlanner:
    def __init__(self, db: Session):
        self.db = db

    def generate_week(self, user: models.UserProfile, week_start: date | None = None) -> models.DietPlan:
        week_start = week_start or self._monday(date.today())
        calories = self._target_calories(user)
        protein = self._target_protein(user)
        daily_budget = user.budget_amount if user.budget_period == "daily" else user.budget_amount / 7
        foods = self._food_bank(user)
        meals, cost = self._build_meals(user, calories, protein, daily_budget, foods)
        rationale = (
            f"Protein target set to {protein}g using {user.diet_preference.replace('_', '-')} foods "
            f"available around {user.location}. Daily cost is capped near Rs {daily_budget:.0f}."
        )

        plan = models.DietPlan(
            user_id=user.id,
            week_start=week_start,
            calories=calories,
            protein_g=protein,
            estimated_daily_cost=cost,
            meals_json=json.dumps(meals),
            rationale=rationale,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def current_plan(self, user_id: int) -> models.DietPlan | None:
        return (
            self.db.query(models.DietPlan)
            .filter(models.DietPlan.user_id == user_id)
            .order_by(desc(models.DietPlan.week_start), desc(models.DietPlan.id))
            .first()
        )

    def serialize_plan(self, plan: models.DietPlan | None) -> dict | None:
        if not plan:
            return None
        return {
            "id": plan.id,
            "week_start": plan.week_start.isoformat(),
            "calories": plan.calories,
            "protein_g": plan.protein_g,
            "estimated_daily_cost": plan.estimated_daily_cost,
            "meals": json.loads(plan.meals_json),
            "rationale": plan.rationale,
        }

    def _target_calories(self, user: models.UserProfile) -> int:
        bmr = 10 * user.weight_kg + 6.25 * user.height_cm - 5 * user.age + 5
        maintenance = bmr * 1.45
        if user.fitness_goal == "fat_loss":
            maintenance -= 450
        elif user.fitness_goal == "muscle_gain":
            maintenance += 250
        return round(maintenance / 25) * 25

    def _target_protein(self, user: models.UserProfile) -> int:
        multiplier = {"fat_loss": 1.8, "muscle_gain": 1.7, "maintenance": 1.4}.get(user.fitness_goal, 1.5)
        return round(user.weight_kg * multiplier)

    def _food_bank(self, user: models.UserProfile) -> list[str]:
        location = user.location.lower()
        if any(word in location for word in ["delhi", "up", "punjab", "haryana", "jaipur", "lucknow"]):
            region = "north"
        elif any(word in location for word in ["bangalore", "chennai", "hyderabad", "kochi", "kerala"]):
            region = "south"
        elif any(word in location for word in ["mumbai", "pune", "gujarat", "ahmedabad"]):
            region = "west"
        elif any(word in location for word in ["kolkata", "odisha", "assam", "bihar"]):
            region = "east"
        else:
            region = "default"
        foods = LOCAL_FOOD_BANK[region]
        if user.diet_preference == "veg":
            return [food for food in foods if food not in {"eggs", "fish"}] + ["soy chunks", "milk"]
        return foods

    def _build_meals(self, user: models.UserProfile, calories: int, protein: int, budget: float, foods: list[str]) -> tuple[list[dict], float]:
        low_budget = budget < 180
        protein_anchor = "soy chunks" if user.diet_preference == "veg" and low_budget else "paneer"
        if user.diet_preference == "non_veg":
            protein_anchor = "eggs" if low_budget else "eggs or chicken"

        meals = [
            {
                "name": "Breakfast",
                "items": [self._pick(foods, ["poha", "dosa", "roti", "rice"]), "curd", protein_anchor],
                "calories": round(calories * 0.25),
                "protein_g": round(protein * 0.25),
                "cost_rs": round(budget * 0.22),
            },
            {
                "name": "Lunch",
                "items": [self._pick(foods, ["roti", "rice"]), "dal", self._pick(foods, ["seasonal sabzi", "seasonal greens"]), protein_anchor],
                "calories": round(calories * 0.35),
                "protein_g": round(protein * 0.35),
                "cost_rs": round(budget * 0.35),
            },
            {
                "name": "Snack",
                "items": ["sprouts" if "sprouts" in foods else "chana", "peanuts", "milk" if user.diet_preference == "veg" else "eggs"],
                "calories": round(calories * 0.15),
                "protein_g": round(protein * 0.15),
                "cost_rs": round(budget * 0.18),
            },
            {
                "name": "Dinner",
                "items": [self._pick(foods, ["roti", "rice"]), self._pick(foods, ["dal", "sambar", "rajma"]), self._pick(foods, ["paneer", "eggs", "fish", "soy chunks"])],
                "calories": round(calories * 0.25),
                "protein_g": round(protein * 0.25),
                "cost_rs": round(budget * 0.25),
            },
        ]
        return meals, sum(meal["cost_rs"] for meal in meals)

    def _pick(self, foods: list[str], candidates: list[str]) -> str:
        for candidate in candidates:
            if candidate in foods:
                return candidate
        return candidates[0]

    def _monday(self, current: date) -> date:
        return current - timedelta(days=current.weekday())
