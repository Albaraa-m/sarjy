import nutrition


async def test_finds_food_and_scales_to_grams():
    result = await nutrition.lookup("chicken breast cooked", 200)
    assert result["status"] == "found"
    assert result["source"] == "USDA FoodData Central"
    assert max(match["protein_g"] for match in result["matches"]) > 40


async def test_reports_food_not_in_database():
    result = await nutrition.lookup("kabsa", 300)
    assert result == {"status": "not_found"}


async def test_reports_unavailable_when_api_fails(monkeypatch):
    monkeypatch.setenv("FDC_API_KEY", "invalid-key")
    result = await nutrition.lookup("white rice cooked", 100)
    assert result == {"status": "unavailable"}
