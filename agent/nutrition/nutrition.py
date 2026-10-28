import logging
import time
from dataclasses import asdict, dataclass
from typing import Literal

import httpx

from . import usda

logger = logging.getLogger("sarjy.nutrition")

# USDA nutrient numbers; SR Legacy and FNDDS foods report every nutrient per 100 g.
NUTRIENTS = {"208": "calories", "203": "protein_g", "205": "carbs_g", "204": "fat_g"}


@dataclass(frozen=True)
class Macros:
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float

    def scaled(self, grams: float) -> Macros:
        """Scales macros given per 100 g to `grams`, rounded to 0.1."""
        factor = grams / 100
        return Macros(
            calories=round(self.calories * factor, 1),
            protein_g=round(self.protein_g * factor, 1),
            carbs_g=round(self.carbs_g * factor, 1),
            fat_g=round(self.fat_g * factor, 1),
        )

    def __add__(self, other: Macros) -> Macros:
        return Macros(
            calories=round(self.calories + other.calories, 1),
            protein_g=round(self.protein_g + other.protein_g, 1),
            carbs_g=round(self.carbs_g + other.carbs_g, 1),
            fat_g=round(self.fat_g + other.fat_g, 1),
        )

    def remaining_after(self, eaten: Macros) -> Macros:
        """What's left of these targets after `eaten`, never below zero."""
        return Macros(
            calories=max(round(self.calories - eaten.calories, 1), 0),
            protein_g=max(round(self.protein_g - eaten.protein_g, 1), 0),
            carbs_g=max(round(self.carbs_g - eaten.carbs_g, 1), 0),
            fat_g=max(round(self.fat_g - eaten.fat_g, 1), 0),
        )


@dataclass(frozen=True)
class UsdaFood:
    fdc_id: int
    description: str
    per_100g: Macros


Source = Literal["usda", "estimate"]


@dataclass(frozen=True)
class Portion:
    """An amount of something the user ate, with its macros for that amount."""

    # What the user and the UI call it: "Banana", not USDA's "Bananas, raw".
    name: str
    usda_description: str | None
    grams: float
    macros: Macros
    source: Source


class Nutrition:
    """Calories and macros for foods, from USDA FoodData Central."""

    def __init__(self):
        # Every USDA food looked up this session, so it can later be logged by its id.
        self._usda_foods: dict[int, UsdaFood] = {}

    async def lookup(self, query: str, grams: float) -> dict:
        """Looks up a generic food and scales its macros to `grams`."""
        start = time.perf_counter()
        try:
            foods = await usda.search(query)
        except httpx.HTTPError as error:
            logger.warning("USDA lookup %r failed after %d ms: %s", query, _ms_since(start), error)
            return {"status": "unavailable"}
        logger.info("USDA lookup %r: %d matches in %d ms", query, len(foods), _ms_since(start))
        if not foods:
            return {"status": "not_found"}
        # SR Legacy first: for common foods both datasets match ("Bananas, raw" at 89 kcal/100 g,
        # "Banana, raw" at 97), and the LLM tends to quote one and log the other.
        foods.sort(key=lambda food: food["dataType"] != "SR Legacy")
        usda_foods = [_usda_food(food) for food in foods]
        self._usda_foods.update({usda_food.fdc_id: usda_food for usda_food in usda_foods})
        return {
            "status": "found",
            "source": "usda",
            "grams": grams,
            "foods": [
                {
                    "fdc_id": usda_food.fdc_id,
                    "description": usda_food.description,
                    **asdict(usda_food.per_100g.scaled(grams)),
                }
                for usda_food in usda_foods
            ],
        }

    def usda_food(self, fdc_id: int) -> UsdaFood | None:
        """A food from an earlier lookup this session, or None if it was never looked up."""
        return self._usda_foods.get(fdc_id)


def _usda_food(food: dict) -> UsdaFood:
    per_100g = dict.fromkeys(NUTRIENTS.values(), 0.0)
    for nutrient in food["foodNutrients"]:
        name = NUTRIENTS.get(nutrient.get("nutrientNumber"))
        if name:
            per_100g[name] = nutrient["value"]
    return UsdaFood(
        fdc_id=food["fdcId"], description=food["description"], per_100g=Macros(**per_100g)
    )


def _ms_since(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)
