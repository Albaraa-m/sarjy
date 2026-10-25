from nutrition import Nutrition


async def test_finds_food_and_scales_to_grams(user_id):
    result = await Nutrition(user_id).lookup("chicken breast cooked", 200)
    assert result["status"] == "found"
    assert result["source"] == "usda"
    assert max(match["protein_g"] for match in result["matches"]) > 40


async def test_reports_food_not_in_database(user_id):
    result = await Nutrition(user_id).lookup("kabsa", 300)
    assert result == {"status": "not_found"}


async def test_reports_unavailable_when_api_fails(user_id, monkeypatch):
    monkeypatch.setenv("FDC_API_KEY", "invalid-key")
    result = await Nutrition(user_id).lookup("white rice cooked", 100)
    assert result == {"status": "unavailable"}


async def test_sums_todays_entries(user_id):
    nutrition = Nutrition(user_id)
    await nutrition.log("chicken breast", 200, 394, 59.6, 0, 15.6, "usda")
    today = await nutrition.log("white rice", 150, 195, 4, 42, 0.4, "estimate")

    assert today["totals"] == {"calories": 589, "protein_g": 63.6, "carbs_g": 42, "fat_g": 16}
    assert [entry["food"] for entry in today["entries"]] == ["chicken breast", "white rice"]
