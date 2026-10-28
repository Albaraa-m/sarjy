from datetime import date

from nutrition import db as nutrition_db
from nutrition.models import Macros, Portion

TODAY = date(2026, 10, 27)
BANANA = Portion(
    name="Banana",
    usda_description="Bananas, raw",
    grams=118,
    macros=Macros(calories=105, protein_g=1.3, carbs_g=27, fat_g=0.4),
    source="usda",
)
KABSA = Portion(
    name="Chicken kabsa",
    usda_description=None,
    grams=400,
    macros=Macros(calories=700, protein_g=40, carbs_g=80, fat_g=20),
    source="estimate",
)


async def test_returns_the_days_foods_in_order(user_id):
    await nutrition_db.save(user_id, TODAY, [BANANA, KABSA])
    assert await nutrition_db.eaten_on(user_id, TODAY) == [BANANA, KABSA]


async def test_other_days_and_users_are_separate(user_id):
    await nutrition_db.save(user_id, TODAY, [BANANA])
    assert await nutrition_db.eaten_on(user_id, date(2026, 10, 26)) == []
    assert await nutrition_db.eaten_on(f"{user_id}-other", TODAY) == []
