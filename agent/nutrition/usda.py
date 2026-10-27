import os

import httpx

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
# Generic foods ("chicken breast, roasted") and prepared dishes ("burrito, beef and bean"), not brands.
DATA_TYPES = ["SR Legacy", "Survey (FNDDS)"]


async def search(food: str) -> list[dict]:
    """Searches USDA FoodData Central. Raises httpx.HTTPError on failure."""
    # POST takes the data types as a JSON list; GET with a comma-separated list randomly returns 400.
    body = {"query": food, "dataType": DATA_TYPES, "pageSize": 3}
    # DEMO_KEY works without signup but allows only 30 requests per hour.
    params = {"api_key": os.environ.get("FDC_API_KEY", "DEMO_KEY")}
    async with httpx.AsyncClient(timeout=3) as client:
        response = await client.post(SEARCH_URL, params=params, json=body)
        response.raise_for_status()
    return response.json()["foods"]
