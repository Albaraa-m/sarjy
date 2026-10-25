import os

import httpx

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"


async def search(food: str) -> list[dict]:
    """Searches USDA FoodData Central's generic foods. Raises httpx.HTTPError on failure."""
    params = {
        "query": food,
        "dataType": "SR Legacy",  # generic foods ("chicken breast, roasted"), not brands
        "pageSize": 3,
        # DEMO_KEY works without signup but allows only 30 requests per hour.
        "api_key": os.environ.get("FDC_API_KEY", "DEMO_KEY"),
    }
    async with httpx.AsyncClient(timeout=3) as client:
        response = await client.get(SEARCH_URL, params=params)
        response.raise_for_status()
    return response.json()["foods"]
