import json
from datetime import UTC, date, datetime

import pytest

from nutrition import FoodEntry, FoodMatch, Macros, Nutrition
from nutrition import db as nutrition_db
from nutrition.food_log import DAILY_TARGETS, DaySummary, FoodLog, riyadh_day, today

BANANA = FoodMatch(id=1, description="Bananas, raw", per_100g=Macros(89, 1.09, 22.84, 0.33))
RICE = FoodMatch(id=2, description="Rice, white, cooked", per_100g=Macros(130, 2.4, 28.6, 0.2))


class StubNutrition(Nutrition):
    """Two foods already looked up, so tests don't call USDA."""

    def match(self, match_id: int) -> FoodMatch | None:
        return {BANANA.id: BANANA, RICE.id: RICE}.get(match_id)


@pytest.fixture
def changes() -> list[DaySummary]:
    return []


@pytest.fixture
async def food_log(user_id, changes) -> FoodLog:
    async def record(summary: DaySummary) -> None:
        changes.append(summary)

    return await FoodLog.load(user_id, StubNutrition(), on_change=record)


async def test_prepare_does_not_save(food_log, user_id):
    summary = await food_log.prepare(BANANA.id, 118)
    assert summary is not None
    assert summary.pending is not None
    assert summary.pending.macros == BANANA.per_100g.scaled(118)
    assert await nutrition_db.foods_on(user_id, today()) == []


async def test_confirm_saves_the_looked_up_values(food_log, user_id):
    await food_log.prepare(BANANA.id, 118)
    summary = await food_log.confirm()
    assert summary is not None
    assert summary.pending is None
    [saved] = await nutrition_db.foods_on(user_id, today())
    assert (saved.food, saved.grams, saved.source) == ("Bananas, raw", 118, "usda")
    assert saved.macros == BANANA.per_100g.scaled(118)


async def test_confirm_twice_saves_once(food_log, user_id):
    await food_log.prepare(BANANA.id, 118)
    await food_log.confirm()
    assert await food_log.confirm() is None
    assert len(await nutrition_db.foods_on(user_id, today())) == 1


async def test_cancel_clears_pending(food_log, user_id):
    await food_log.prepare(BANANA.id, 118)
    summary = await food_log.cancel()
    assert summary.pending is None
    assert await food_log.confirm() is None
    assert await nutrition_db.foods_on(user_id, today()) == []


async def test_new_prepare_replaces_pending(food_log, user_id):
    await food_log.prepare(BANANA.id, 118)
    await food_log.prepare(RICE.id, 150)
    await food_log.confirm()
    [saved] = await nutrition_db.foods_on(user_id, today())
    assert saved.food == RICE.description


async def test_unknown_food_id_is_rejected(food_log):
    assert await food_log.prepare(999, 100) is None


async def test_estimate_is_saved_as_estimate(food_log, user_id):
    await food_log.prepare_estimate("Al Baik broast", 400, Macros(900, 50, 60, 50))
    await food_log.confirm()
    [saved] = await nutrition_db.foods_on(user_id, today())
    assert saved.source == "estimate"
    assert saved.macros == Macros(900, 50, 60, 50)


async def test_totals_and_remaining(food_log):
    await food_log.prepare(BANANA.id, 100)
    await food_log.confirm()
    await food_log.prepare(RICE.id, 100)
    summary = await food_log.confirm()
    assert summary is not None
    assert summary.totals == Macros(219, 3.5, 51.4, 0.5)
    assert summary.remaining.calories == DAILY_TARGETS.calories - 219


async def test_reports_every_change(food_log, changes):
    await food_log.prepare(BANANA.id, 118)
    await food_log.confirm()
    await food_log.prepare(RICE.id, 150)
    await food_log.cancel()
    assert [summary.pending is not None for summary in changes] == [True, False, True, False]


def test_today_is_the_riyadh_day():
    assert riyadh_day(datetime(2026, 10, 27, 20, 30, tzinfo=UTC)) == date(2026, 10, 27)
    assert riyadh_day(datetime(2026, 10, 27, 21, 30, tzinfo=UTC)) == date(2026, 10, 28)


def test_summary_json_shape():
    banana = FoodEntry("Bananas, raw", 118, Macros(105, 1.3, 27, 0.4), "usda")
    summary = DaySummary(
        date(2026, 10, 27), [banana], None, banana.macros, DAILY_TARGETS, DAILY_TARGETS
    )
    assert json.loads(summary.to_json()) == {
        "day": "2026-10-27",
        "entries": [
            {
                "food": "Bananas, raw",
                "grams": 118,
                "macros": {"calories": 105, "protein_g": 1.3, "carbs_g": 27, "fat_g": 0.4},
                "source": "usda",
            }
        ],
        "pending": None,
        "totals": {"calories": 105, "protein_g": 1.3, "carbs_g": 27, "fat_g": 0.4},
        "targets": {"calories": 2200, "protein_g": 150, "carbs_g": 220, "fat_g": 70},
        "remaining": {"calories": 2200, "protein_g": 150, "carbs_g": 220, "fat_g": 70},
    }


async def test_load_starts_from_todays_saved_foods(user_id):
    banana = FoodEntry("Bananas, raw", 118, Macros(105, 1.3, 27, 0.4), "usda")
    await nutrition_db.add_food(user_id, today(), banana)

    async def ignore(summary: DaySummary) -> None:
        pass

    food_log = await FoodLog.load(user_id, StubNutrition(), on_change=ignore)
    assert food_log.summary().entries == [banana]
