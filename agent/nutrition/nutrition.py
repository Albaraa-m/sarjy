import logging
import time

import httpx

from . import usda
from .models import Macros, UsdaFood

logger = logging.getLogger("sarjy.nutrition")

# USDA nutrient numbers; SR Legacy and FNDDS foods report every nutrient per 100 g.
NUTRIENTS = {"208": "calories", "203": "protein_g", "205": "carbs_g", "204": "fat_g"}


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
                    **usda_food.per_100g.scaled(grams).model_dump(),
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
