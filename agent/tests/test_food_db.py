from datetime import date

from nutrition import FoodEntry, Macros
from nutrition import db as nutrition_db

TODAY = date(2026, 10, 27)
BANANA = FoodEntry("banana", 118, Macros(105, 1.3, 27, 0.4), "usda")
KABSA = FoodEntry("chicken kabsa", 400, Macros(700, 40, 80, 20), "estimate")


async def test_returns_the_days_foods_in_order(user_id):
    await nutrition_db.add_foods(user_id, TODAY, [BANANA, KABSA])
    assert await nutrition_db.foods_on(user_id, TODAY) == [BANANA, KABSA]


async def test_other_days_and_users_are_separate(user_id):
    await nutrition_db.add_foods(user_id, TODAY, [BANANA])
    assert await nutrition_db.foods_on(user_id, date(2026, 10, 26)) == []
    assert await nutrition_db.foods_on(f"{user_id}-other", TODAY) == []
