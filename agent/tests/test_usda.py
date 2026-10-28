import httpx
import pytest
from pydantic import SecretStr, ValidationError

from nutrition import usda
from nutrition.models import Macros
from settings import settings


async def test_finds_generic_foods():
    foods = await usda.search("chicken breast cooked")
    assert max(food.per_100g.protein_g for food in foods) > 20


async def test_finds_prepared_dishes():
    foods = await usda.search("beef and bean burrito")
    assert any("burrito" in food.description.lower() for food in foods)


async def test_finds_nothing_for_dishes_usda_lacks():
    assert await usda.search("kabsa") == []


async def test_raises_when_the_api_fails(monkeypatch):
    monkeypatch.setattr(settings, "fdc_api_key", SecretStr("invalid-key"))
    with pytest.raises(httpx.HTTPStatusError):
        await usda.search("white rice cooked")


async def test_prefers_sr_legacy_when_both_datasets_match():
    # A 118 g banana was spoken as 105 kcal (SR Legacy) but logged as 115 (FNDDS "Banana, raw").
    [first, *_] = await usda.search("bananas raw")
    assert first.description == "Bananas, raw"
    assert first.per_100g.scaled(118).calories == 105.0


def test_parses_usda_foods_sr_legacy_first():
    response = b"""{"foods": [
        {"fdcId": 2, "description": "Banana, raw", "dataType": "Survey (FNDDS)",
         "foodNutrients": [{"nutrientNumber": "208", "value": 97}]},
        {"fdcId": 1, "description": "Bananas, raw", "dataType": "SR Legacy",
         "foodNutrients": [{"nutrientNumber": "208", "value": 89},
                           {"nutrientNumber": "203", "value": 1.09},
                           {"nutrientNumber": "301", "value": 5}]}
    ]}"""
    [sr_legacy, fndds] = usda.parse_foods(response)
    assert (sr_legacy.fdc_id, fndds.fdc_id) == (1, 2)
    assert sr_legacy.per_100g == Macros(calories=89, protein_g=1.09, carbs_g=0, fat_g=0)


def test_malformed_usda_reply_is_rejected():
    with pytest.raises(ValidationError):
        usda.parse_foods(b'{"foods": [{"description": "Banana"}]}')
