import httpx
from pydantic import BaseModel, Field

from settings import settings

from .models import Macros, UsdaFood

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
# Generic foods ("chicken breast, roasted") and prepared dishes ("burrito, beef and bean"), not brands.
DATA_TYPES = ("SR Legacy", "Survey (FNDDS)")
# SR Legacy and FNDDS foods report every nutrient per 100 g.
MACRO_BY_NUTRIENT_NUMBER = {"208": "calories", "203": "protein_g", "205": "carbs_g", "204": "fat_g"}


async def search(query: str) -> list[UsdaFood]:
    """Up to three foods matching `query`, SR Legacy first.
    Raises httpx.HTTPError if USDA fails, pydantic.ValidationError if its reply is malformed."""
    # POST takes the data types as a JSON list; GET with a comma-separated list randomly returns 400.
    body = {"query": query, "dataType": DATA_TYPES, "pageSize": 3}
    params = {"api_key": settings.fdc_api_key.get_secret_value()}
    async with httpx.AsyncClient(timeout=3) as client:
        response = await client.post(SEARCH_URL, params=params, json=body)
        response.raise_for_status()
    return parse_foods(response.content)


def parse_foods(search_response: bytes) -> list[UsdaFood]:
    foods = _SearchResponse.model_validate_json(search_response).foods
    # For common foods both datasets match ("Bananas, raw" at 89 kcal/100 g, "Banana, raw" at 97),
    # and the LLM tends to quote one and log the other.
    sr_legacy_first = sorted(foods, key=lambda food: food.data_type != "SR Legacy")
    return [food.to_usda_food() for food in sr_legacy_first]


class _Nutrient(BaseModel):
    number: str = Field(alias="nutrientNumber")
    value: float


class _Food(BaseModel):
    fdc_id: int = Field(alias="fdcId")
    description: str
    data_type: str = Field(alias="dataType")
    nutrients: list[_Nutrient] = Field(alias="foodNutrients")

    def to_usda_food(self) -> UsdaFood:
        per_100g = dict.fromkeys(MACRO_BY_NUTRIENT_NUMBER.values(), 0.0)
        for nutrient in self.nutrients:
            if macro := MACRO_BY_NUTRIENT_NUMBER.get(nutrient.number):
                per_100g[macro] = nutrient.value
        return UsdaFood(
            fdc_id=self.fdc_id, description=self.description, per_100g=Macros(**per_100g)
        )


class _SearchResponse(BaseModel):
    foods: list[_Food]
