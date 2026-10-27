import asyncio
import json
from datetime import UTC, date, datetime

import pytest

from nutrition import FoodEntry, FoodMatch, Macros, Nutrition
from nutrition import db as nutrition_db
from nutrition.food_log import DAILY_TARGETS, DaySummary, FoodLog, riyadh_day, today

EGGS = FoodMatch(id=1, description="Egg, scrambled", per_100g=Macros(149, 10, 1.6, 11))
TOAST = FoodMatch(id=2, description="Bread, whole wheat, toasted", per_100g=Macros(306, 13, 51, 4))
MILK = FoodMatch(id=3, description="Milk, whole", per_100g=Macros(61, 3.2, 4.8, 3.3))


class StubNutrition(Nutrition):
    """Three foods already looked up, so tests don't call USDA."""

    def match(self, match_id: int) -> FoodMatch | None:
        return {food.id: food for food in (EGGS, TOAST, MILK)}.get(match_id)


@pytest.fixture
def changes() -> list[DaySummary]:
    return []


@pytest.fixture
async def food_log(user_id, changes) -> FoodLog:
    async def record(summary: DaySummary) -> None:
        changes.append(summary)

    return await FoodLog.load(user_id, StubNutrition(), on_change=record)


async def prepare_breakfast(food_log: FoodLog) -> None:
    await food_log.prepare(EGGS.id, 150)
    await food_log.prepare(TOAST.id, 60)
    await food_log.prepare(MILK.id, 244)


def foods(entries: list[FoodEntry]) -> list[str]:
    return [entry.food for entry in entries]


async def test_prepare_does_not_save(food_log, user_id):
    await prepare_breakfast(food_log)
    assert foods(food_log.summary().pending) == [
        EGGS.description,
        TOAST.description,
        MILK.description,
    ]
    assert await nutrition_db.foods_on(user_id, today()) == []


async def test_parallel_prepares_all_stay_pending(food_log):
    # In a live call the LLM prepared eggs, toast and milk at once; with a single pending slot
    # only the last one survived.
    await asyncio.gather(
        food_log.prepare(EGGS.id, 150),
        food_log.prepare(TOAST.id, 60),
        food_log.prepare(MILK.id, 244),
    )
    assert len(food_log.summary().pending) == 3


async def test_preparing_a_pending_food_again_replaces_it(food_log):
    await prepare_breakfast(food_log)
    await food_log.prepare(EGGS.id, 100)
    pending = food_log.summary().pending
    assert foods(pending) == [TOAST.description, MILK.description, EGGS.description]
    assert pending[-1].grams == 100


async def test_confirm_saves_all_pending_foods(food_log, user_id):
    await prepare_breakfast(food_log)
    summary = await food_log.confirm()
    assert summary is not None
    assert summary.pending == []
    saved = await nutrition_db.foods_on(user_id, today())
    assert foods(saved) == [EGGS.description, TOAST.description, MILK.description]
    assert saved[0].macros == EGGS.per_100g.scaled(150)
    assert summary.totals.calories == round(sum(entry.macros.calories for entry in saved), 1)


async def test_confirm_twice_saves_once(food_log, user_id):
    await prepare_breakfast(food_log)
    await food_log.confirm()
    assert await food_log.confirm() is None
    assert len(await nutrition_db.foods_on(user_id, today())) == 3


async def test_parallel_confirms_save_once(food_log, user_id):
    # The LLM sent confirm_food_log several times in one turn; both passed the pending check
    # before either finished saving, so the second appended None and broke every later summary.
    await prepare_breakfast(food_log)
    results = await asyncio.gather(food_log.confirm(), food_log.confirm())
    assert sum(result is not None for result in results) == 1
    assert len(await nutrition_db.foods_on(user_id, today())) == 3
    assert len(food_log.summary().entries) == 3


async def test_failed_save_keeps_foods_pending(food_log, user_id, monkeypatch):
    async def fail(*args) -> None:
        raise TimeoutError

    await prepare_breakfast(food_log)
    with monkeypatch.context() as patch:
        patch.setattr(nutrition_db, "add_foods", fail)
        with pytest.raises(TimeoutError):
            await food_log.confirm()
    assert len(food_log.summary().pending) == 3
    assert food_log.summary().entries == []

    await food_log.confirm()
    assert len(await nutrition_db.foods_on(user_id, today())) == 3


async def test_cancel_one_food_keeps_the_others(food_log, user_id):
    await prepare_breakfast(food_log)
    await food_log.cancel(MILK.description)
    await food_log.confirm()
    saved = await nutrition_db.foods_on(user_id, today())
    assert foods(saved) == [EGGS.description, TOAST.description]


async def test_cancel_all(food_log, user_id):
    await prepare_breakfast(food_log)
    summary = await food_log.cancel()
    assert summary.pending == []
    assert await food_log.confirm() is None
    assert await nutrition_db.foods_on(user_id, today()) == []


async def test_unknown_food_id_is_rejected(food_log):
    assert await food_log.prepare(999, 100) is None


async def test_estimate_is_saved_as_estimate(food_log, user_id):
    await food_log.prepare_estimate("Al Baik broast", 400, Macros(900, 50, 60, 50))
    await food_log.confirm()
    [saved] = await nutrition_db.foods_on(user_id, today())
    assert saved.source == "estimate"
    assert saved.macros == Macros(900, 50, 60, 50)


async def test_totals_and_remaining(food_log):
    await food_log.prepare(EGGS.id, 100)
    await food_log.prepare(MILK.id, 100)
    summary = await food_log.confirm()
    assert summary is not None
    assert summary.totals == Macros(210, 13.2, 6.4, 14.3)
    assert summary.remaining.calories == DAILY_TARGETS.calories - 210


async def test_reports_every_change(food_log, changes):
    await food_log.prepare(EGGS.id, 150)
    await food_log.prepare(MILK.id, 244)
    await food_log.confirm()
    await food_log.prepare(TOAST.id, 60)
    await food_log.cancel()
    assert [len(summary.pending) for summary in changes] == [1, 2, 0, 1, 0]


async def test_load_starts_from_todays_saved_foods(user_id):
    milk = FoodEntry(MILK.description, 244, MILK.per_100g.scaled(244), "usda")
    await nutrition_db.add_foods(user_id, today(), [milk])

    async def ignore(summary: DaySummary) -> None:
        pass

    food_log = await FoodLog.load(user_id, StubNutrition(), on_change=ignore)
    assert food_log.summary().entries == [milk]


def test_today_is_the_riyadh_day():
    assert riyadh_day(datetime(2026, 10, 27, 20, 30, tzinfo=UTC)) == date(2026, 10, 27)
    assert riyadh_day(datetime(2026, 10, 27, 21, 30, tzinfo=UTC)) == date(2026, 10, 28)


def test_summary_json_shape():
    milk = FoodEntry("Milk, whole", 244, Macros(149, 7.8, 11.7, 8.1), "usda")
    summary = DaySummary(
        date(2026, 10, 27), [], [milk], Macros(0, 0, 0, 0), DAILY_TARGETS, DAILY_TARGETS
    )
    assert json.loads(summary.to_json()) == {
        "day": "2026-10-27",
        "entries": [],
        "pending": [
            {
                "food": "Milk, whole",
                "grams": 244,
                "macros": {"calories": 149, "protein_g": 7.8, "carbs_g": 11.7, "fat_g": 8.1},
                "source": "usda",
            }
        ],
        "totals": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0},
        "targets": {"calories": 2200, "protein_g": 150, "carbs_g": 220, "fat_g": 70},
        "remaining": {"calories": 2200, "protein_g": 150, "carbs_g": 220, "fat_g": 70},
    }
