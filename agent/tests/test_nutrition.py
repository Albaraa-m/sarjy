from pydantic import SecretStr

from nutrition import Macros, Nutrition
from settings import settings


async def test_finds_food_and_scales_to_grams():
    result = await Nutrition().lookup("chicken breast cooked", 200)
    assert result["status"] == "found"
    assert result["source"] == "usda"
    assert max(food["protein_g"] for food in result["foods"]) > 40


async def test_finds_prepared_dishes():
    result = await Nutrition().lookup("beef and bean burrito", 250)
    assert result["status"] == "found"
    assert any("burrito" in food["description"].lower() for food in result["foods"])


async def test_reports_food_not_in_database():
    result = await Nutrition().lookup("kabsa", 300)
    assert result == {"status": "not_found"}


async def test_reports_unavailable_when_api_fails(monkeypatch):
    monkeypatch.setattr(settings, "fdc_api_key", SecretStr("invalid-key"))
    result = await Nutrition().lookup("white rice cooked", 100)
    assert result == {"status": "unavailable"}


def test_scales_macros_from_100_grams():
    banana = Macros(calories=89, protein_g=1.09, carbs_g=22.84, fat_g=0.33)
    assert banana.scaled(118) == Macros(calories=105.0, protein_g=1.3, carbs_g=27.0, fat_g=0.4)


async def test_remembers_usda_foods_by_id():
    nutrition = Nutrition()
    result = await nutrition.lookup("banana", 118)
    first = result["foods"][0]
    usda_food = nutrition.usda_food(first["fdc_id"])
    assert usda_food is not None
    assert usda_food.description == first["description"]
    assert usda_food.per_100g.scaled(118).calories == first["calories"]


def test_unknown_fdc_id_is_none():
    assert Nutrition().usda_food(123) is None


async def test_prefers_sr_legacy_when_both_datasets_match():
    # A 118 g banana was spoken as 105 kcal (SR Legacy) but logged as 115 (FNDDS "Banana, raw").
    result = await Nutrition().lookup("bananas raw", 118)
    assert result["foods"][0]["description"] == "Bananas, raw"
    assert result["foods"][0]["calories"] == 105.0
