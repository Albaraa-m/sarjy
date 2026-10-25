import logging
import time

import httpx

from . import usda

logger = logging.getLogger("sarjy.nutrition")

# USDA nutrient numbers; SR Legacy foods report every nutrient per 100 g.
NUTRIENTS = {"208": "calories", "203": "protein_g", "205": "carbs_g", "204": "fat_g"}


class Nutrition:
    """Calories and macros for foods, from USDA FoodData Central."""

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
        return {
            "status": "found",
            "source": "usda",
            "grams": grams,
            "matches": [_macros(food_item, grams) for food_item in foods],
        }


def _macros(food_item: dict, grams: float) -> dict:
    macros = {"description": food_item["description"]}
    for nutrient in food_item["foodNutrients"]:
        name = NUTRIENTS.get(nutrient.get("nutrientNumber"))
        if name:
            macros[name] = round(nutrient["value"] * grams / 100, 1)
    return macros


def _ms_since(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)
