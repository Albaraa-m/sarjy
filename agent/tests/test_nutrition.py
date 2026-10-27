from nutrition import Macros, Nutrition


async def test_finds_food_and_scales_to_grams():
    result = await Nutrition().lookup("chicken breast cooked", 200)
    assert result["status"] == "found"
    assert result["source"] == "usda"
    assert max(match["protein_g"] for match in result["matches"]) > 40


async def test_finds_prepared_dishes():
    result = await Nutrition().lookup("beef and bean burrito", 250)
    assert result["status"] == "found"
    assert any("burrito" in match["description"].lower() for match in result["matches"])


async def test_reports_food_not_in_database():
    result = await Nutrition().lookup("kabsa", 300)
    assert result == {"status": "not_found"}


async def test_reports_unavailable_when_api_fails(monkeypatch):
    monkeypatch.setenv("FDC_API_KEY", "invalid-key")
    result = await Nutrition().lookup("white rice cooked", 100)
    assert result == {"status": "unavailable"}


def test_scales_macros_from_100_grams():
    banana = Macros(calories=89, protein_g=1.09, carbs_g=22.84, fat_g=0.33)
    assert banana.scaled(118) == Macros(calories=105.0, protein_g=1.3, carbs_g=27.0, fat_g=0.4)


async def test_remembers_matches_by_id():
    nutrition = Nutrition()
    result = await nutrition.lookup("banana", 118)
    first = result["matches"][0]
    match = nutrition.match(first["id"])
    assert match is not None
    assert match.description == first["description"]
    assert match.per_100g.scaled(118).calories == first["calories"]


def test_unknown_match_id_is_none():
    assert Nutrition().match(123) is None
