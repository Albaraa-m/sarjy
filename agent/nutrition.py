import logging
import os

import httpx

logger = logging.getLogger("sarjy.nutrition")

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
SOURCE = "USDA FoodData Central"

# USDA nutrient numbers; SR Legacy foods report every nutrient per 100 g.
NUTRIENTS = {"208": "calories", "203": "protein_g", "205": "carbs_g", "204": "fat_g"}


async def lookup(food: str, grams: float) -> dict:
    """Looks up a generic food in USDA FoodData Central and scales its macros to `grams`."""
    params = {
        "query": food,
        "dataType": "SR Legacy",  # generic foods ("chicken breast, roasted"), not brands
        "pageSize": 3,
        # DEMO_KEY works without signup but allows only 30 requests per hour.
        "api_key": os.environ.get("FDC_API_KEY", "DEMO_KEY"),
    }
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(SEARCH_URL, params=params)
            response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("USDA lookup failed: %s", error)
        return {"status": "unavailable"}

    foods = response.json()["foods"]
    if not foods:
        return {"status": "not_found"}
    return {
        "status": "found",
        "source": SOURCE,
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
