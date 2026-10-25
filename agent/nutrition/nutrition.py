import logging
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from . import db, usda

logger = logging.getLogger("sarjy.nutrition")

# The agent runs in UTC, but "today" should follow the user's day in Saudi Arabia.
TIMEZONE = ZoneInfo("Asia/Riyadh")
MACROS = ("calories", "protein_g", "carbs_g", "fat_g")
# USDA nutrient numbers; SR Legacy foods report every nutrient per 100 g.
NUTRIENTS = {"208": "calories", "203": "protein_g", "205": "carbs_g", "204": "fat_g"}


class Nutrition:
    """Nutrition facts from USDA and what one user ate, grouped by day."""

    def __init__(self, user_id: str):
        self.user_id = user_id

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

    async def log(
        self,
        food: str,
        grams: float,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        source: str,
    ) -> dict:
        """Records food eaten today and returns today's totals."""
        await db.add_food(
            self.user_id, _today(), food, grams, calories, protein_g, carbs_g, fat_g, source
        )
        logger.info("logged %r (%g g, %g kcal, source=%s)", food, grams, calories, source)
        return await self.today()

    async def today(self) -> dict:
        entries = await db.foods_on(self.user_id, _today())
        totals = {macro: round(sum(entry[macro] for entry in entries), 1) for macro in MACROS}
        return {"totals": totals, "entries": entries}


def _macros(food_item: dict, grams: float) -> dict:
    macros = {"description": food_item["description"]}
    for nutrient in food_item["foodNutrients"]:
        name = NUTRIENTS.get(nutrient.get("nutrientNumber"))
        if name:
            macros[name] = round(nutrient["value"] * grams / 100, 1)
    return macros


def _ms_since(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def _today() -> date:
    return datetime.now(TIMEZONE).date()
