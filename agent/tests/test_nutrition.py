from nutrition import Nutrition


async def test_finds_food_and_scales_to_grams():
    result = await Nutrition().lookup("chicken breast cooked", 200)
    assert result["status"] == "found"
    assert result["source"] == "usda"
    assert max(match["protein_g"] for match in result["matches"]) > 40


async def test_reports_food_not_in_database():
    result = await Nutrition().lookup("kabsa", 300)
    assert result == {"status": "not_found"}


async def test_reports_unavailable_when_api_fails(monkeypatch):
    monkeypatch.setenv("FDC_API_KEY", "invalid-key")
    result = await Nutrition().lookup("white rice cooked", 100)
    assert result == {"status": "unavailable"}
