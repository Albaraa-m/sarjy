import logging
import time

import httpx
from pydantic import ValidationError

from . import usda
from .models import UsdaFood

logger = logging.getLogger("sarjy.nutrition")


class Nutrition:
    """Calories and macros for foods, from USDA FoodData Central."""

    def __init__(self):
        # Every USDA food looked up this session, so it can later be logged by its id.
        self._usda_foods: dict[int, UsdaFood] = {}

    async def lookup(self, query: str, grams: float) -> dict:
        """Looks up a generic food and scales its macros to `grams`."""
        start = time.perf_counter()
        try:
            usda_foods = await usda.search(query)
        except (httpx.HTTPError, ValidationError) as error:
            logger.warning("USDA lookup %r failed after %d ms: %s", query, _ms_since(start), error)
            return {"status": "unavailable"}
        logger.info("USDA lookup %r: %d matches in %d ms", query, len(usda_foods), _ms_since(start))
        if not usda_foods:
            return {"status": "not_found"}
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


def _ms_since(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)
