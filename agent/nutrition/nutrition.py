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


@dataclass(frozen=True)
class FoodMatch:
    id: int
    description: str
    per_100g: Macros


Source = Literal["usda", "estimate"]


@dataclass(frozen=True)
class FoodEntry:
    """One food portion the user ate, with its macros for that portion."""

    food: str
    # What the UI shows: "Banana", not USDA's "Bananas, raw".
    display_name: str
    grams: float
    macros: Macros
    source: Source


class Nutrition:
    """Calories and macros for foods, from USDA FoodData Central."""

    def __init__(self):
        # Every match looked up this session, so a food can later be logged by its id.
        self._matches: dict[int, FoodMatch] = {}

    async def lookup(self, food: str, grams: float) -> dict:
        """Looks up a generic food and scales its macros to `grams`."""
        start = time.perf_counter()
        try:
            foods = await usda.search(food)
        except httpx.HTTPError as error:
            logger.warning("USDA lookup %r failed after %d ms: %s", food, _ms_since(start), error)
            return {"status": "unavailable"}
        logger.info("USDA lookup %r: %d matches in %d ms", food, len(foods), _ms_since(start))
        if not foods:
            return {"status": "not_found"}
        # SR Legacy first: for common foods both datasets match ("Bananas, raw" at 89 kcal/100 g,
        # "Banana, raw" at 97), and the LLM tends to quote one and log the other.
        foods.sort(key=lambda food_item: food_item["dataType"] != "SR Legacy")
        matches = [_food_match(food_item) for food_item in foods]
        self._matches.update({match.id: match for match in matches})
        return {
            "status": "found",
            "source": "usda",
            "grams": grams,
            "matches": [
                {
                    "id": match.id,
                    "description": match.description,
                    **asdict(match.per_100g.scaled(grams)),
                }
                for match in matches
            ],
        }

    def match(self, match_id: int) -> FoodMatch | None:
        """A match from an earlier lookup this session, or None if it was never looked up."""
        return self._matches.get(match_id)


def _food_match(food_item: dict) -> FoodMatch:
    per_100g = dict.fromkeys(NUTRIENTS.values(), 0.0)
    for nutrient in food_item["foodNutrients"]:
        name = NUTRIENTS.get(nutrient.get("nutrientNumber"))
        if name:
            per_100g[name] = nutrient["value"]
    return FoodMatch(
        id=food_item["fdcId"], description=food_item["description"], per_100g=Macros(**per_100g)
    )


def _ms_since(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)
