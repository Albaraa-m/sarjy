from food_log import FoodLog


async def test_sums_todays_entries(user_id):
    log = FoodLog(user_id)
    await log.add("chicken breast", 200, 394, 59.6, 0, 15.6, "usda")
    await log.add("white rice", 150, 195, 4, 42, 0.4, "estimate")

    today = await log.today()
    assert today["totals"] == {"calories": 589, "protein_g": 63.6, "carbs_g": 42, "fat_g": 16}
    assert [entry["food"] for entry in today["entries"]] == ["chicken breast", "white rice"]
