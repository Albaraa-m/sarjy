import asyncio
import json
from datetime import UTC, date, datetime

import pytest

from nutrition import DailyIntake, Diary, Macros, Portion, UsdaFood
from nutrition import db as nutrition_db
from nutrition.diary import DAILY_TARGETS, riyadh_day, today
from nutrition.models import NO_MACROS

EGGS = UsdaFood(
    fdc_id=1,
    description="Egg, scrambled",
    per_100g=Macros(calories=149, protein_g=10, carbs_g=1.6, fat_g=11),
)
TOAST = UsdaFood(
    fdc_id=2,
    description="Bread, whole wheat, toasted",
    per_100g=Macros(calories=306, protein_g=13, carbs_g=51, fat_g=4),
)
MILK = UsdaFood(
    fdc_id=3,
    description="Milk, whole",
    per_100g=Macros(calories=61, protein_g=3.2, carbs_g=4.8, fat_g=3.3),
)


@pytest.fixture
def changes() -> list[DailyIntake]:
    return []


@pytest.fixture
async def diary(user_id, changes) -> Diary:
    async def record(intake: DailyIntake) -> None:
        changes.append(intake)

    return await Diary.load(user_id, on_change=record)


async def propose_breakfast(diary: Diary) -> None:
    await diary.propose(EGGS.portion(150, "Scrambled eggs"))
    await diary.propose(TOAST.portion(60, "Toast"))
    await diary.propose(MILK.portion(244, "Milk"))


def descriptions(portions: list[Portion]) -> list[str | None]:
    return [portion.usda_description for portion in portions]


async def test_propose_does_not_save(diary, user_id):
    await propose_breakfast(diary)
    assert descriptions(diary.intake().pending) == [
        EGGS.description,
        TOAST.description,
        MILK.description,
    ]
    assert await nutrition_db.eaten_on(user_id, today()) == []


async def test_parallel_proposals_all_stay_pending(diary):
    # In a live call the LLM prepared eggs, toast and milk at once; with a single pending slot
    # only the last one survived.
    await asyncio.gather(
        diary.propose(EGGS.portion(150, "Scrambled eggs")),
        diary.propose(TOAST.portion(60, "Toast")),
        diary.propose(MILK.portion(244, "Milk")),
    )
    assert len(diary.intake().pending) == 3


async def test_proposing_a_pending_food_again_replaces_it(diary):
    await propose_breakfast(diary)
    await diary.propose(EGGS.portion(100, "Scrambled eggs"))
    pending = diary.intake().pending
    assert descriptions(pending) == [TOAST.description, MILK.description, EGGS.description]
    assert pending[-1].grams == 100


async def test_confirm_saves_all_pending_portions(diary, user_id):
    await propose_breakfast(diary)
    intake = await diary.confirm()
    assert intake is not None
    assert intake.pending == []
    saved = await nutrition_db.eaten_on(user_id, today())
    assert descriptions(saved) == [EGGS.description, TOAST.description, MILK.description]
    assert saved[0].macros == EGGS.per_100g.scaled(150)
    assert intake.totals.calories == round(sum(portion.macros.calories for portion in saved), 1)


async def test_confirm_twice_saves_once(diary, user_id):
    await propose_breakfast(diary)
    await diary.confirm()
    assert await diary.confirm() is None
    assert len(await nutrition_db.eaten_on(user_id, today())) == 3


async def test_parallel_confirms_save_once(diary, user_id):
    # The LLM sent confirm_portions several times in one turn; both passed the pending check
    # before either finished saving, so the second appended None and broke every later summary.
    await propose_breakfast(diary)
    results = await asyncio.gather(diary.confirm(), diary.confirm())
    assert sum(result is not None for result in results) == 1
    assert len(await nutrition_db.eaten_on(user_id, today())) == 3
    assert len(diary.intake().eaten) == 3


async def test_failed_save_keeps_foods_pending(diary, user_id, monkeypatch):
    async def fail(*args) -> None:
        raise TimeoutError

    await propose_breakfast(diary)
    with monkeypatch.context() as patch:
        patch.setattr(nutrition_db, "save", fail)
        with pytest.raises(TimeoutError):
            await diary.confirm()
    assert len(diary.intake().pending) == 3
    assert diary.intake().eaten == []

    await diary.confirm()
    assert len(await nutrition_db.eaten_on(user_id, today())) == 3


async def test_cancel_one_food_keeps_the_others(diary, user_id):
    await propose_breakfast(diary)
    await diary.cancel(MILK.description)
    await diary.confirm()
    saved = await nutrition_db.eaten_on(user_id, today())
    assert descriptions(saved) == [EGGS.description, TOAST.description]


async def test_cancel_by_the_name_sarjy_gave_it(diary, user_id):
    await propose_breakfast(diary)
    await diary.cancel("milk")
    await diary.confirm()
    saved = await nutrition_db.eaten_on(user_id, today())
    assert descriptions(saved) == [EGGS.description, TOAST.description]


async def test_cancel_an_unknown_name_keeps_everything(diary):
    await propose_breakfast(diary)
    assert await diary.cancel("Orange juice") is None
    assert len(diary.intake().pending) == 3


async def test_cancel_all(diary, user_id):
    await propose_breakfast(diary)
    intake = await diary.cancel()
    assert intake.pending == []
    assert await diary.confirm() is None
    assert await nutrition_db.eaten_on(user_id, today()) == []


async def test_name_and_usda_description_are_saved(diary, user_id):
    await diary.propose(MILK.portion(244, "Milk"))
    await diary.confirm()
    [saved] = await nutrition_db.eaten_on(user_id, today())
    assert (saved.name, saved.usda_description) == ("Milk", MILK.description)


async def test_estimate_is_saved_as_estimate(diary, user_id):
    broast = Portion(
        name="Al Baik broast",
        usda_description=None,
        grams=400,
        macros=Macros(calories=900, protein_g=50, carbs_g=60, fat_g=50),
        source="estimate",
    )
    await diary.propose(broast)
    await diary.confirm()
    [saved] = await nutrition_db.eaten_on(user_id, today())
    assert saved.source == "estimate"
    assert saved.macros == Macros(calories=900, protein_g=50, carbs_g=60, fat_g=50)


async def test_totals_and_remaining(diary):
    await diary.propose(EGGS.portion(100, "Scrambled eggs"))
    await diary.propose(MILK.portion(100, "Milk"))
    intake = await diary.confirm()
    assert intake is not None
    assert intake.totals == Macros(calories=210, protein_g=13.2, carbs_g=6.4, fat_g=14.3)
    assert intake.remaining.calories == DAILY_TARGETS.calories - 210


async def test_reports_every_change(diary, changes):
    await diary.propose(EGGS.portion(150, "Scrambled eggs"))
    await diary.propose(MILK.portion(244, "Milk"))
    await diary.confirm()
    await diary.propose(TOAST.portion(60, "Toast"))
    await diary.cancel()
    assert [len(intake.pending) for intake in changes] == [1, 2, 0, 1, 0]


async def test_load_starts_from_todays_saved_portions(user_id):
    milk = Portion(
        name="Milk",
        usda_description=MILK.description,
        grams=244,
        macros=MILK.per_100g.scaled(244),
        source="usda",
    )
    await nutrition_db.save(user_id, today(), [milk])

    async def ignore(intake: DailyIntake) -> None:
        pass

    diary = await Diary.load(user_id, on_change=ignore)
    assert diary.intake().eaten == [milk]


def test_today_is_the_riyadh_day():
    assert riyadh_day(datetime(2026, 10, 27, 20, 30, tzinfo=UTC)) == date(2026, 10, 27)
    assert riyadh_day(datetime(2026, 10, 27, 21, 30, tzinfo=UTC)) == date(2026, 10, 28)


def test_intake_json_shape():
    milk = Portion(
        name="Milk",
        usda_description="Milk, whole",
        grams=244,
        macros=Macros(calories=149, protein_g=7.8, carbs_g=11.7, fat_g=8.1),
        source="usda",
    )
    intake = DailyIntake(
        day=date(2026, 10, 27),
        eaten=[],
        pending=[milk],
        totals=NO_MACROS,
        targets=DAILY_TARGETS,
        remaining=DAILY_TARGETS,
    )
    assert json.loads(intake.model_dump_json()) == {
        "day": "2026-10-27",
        "eaten": [],
        "pending": [
            {
                "name": "Milk",
                "usda_description": "Milk, whole",
                "grams": 244,
                "macros": {"calories": 149, "protein_g": 7.8, "carbs_g": 11.7, "fat_g": 8.1},
                "source": "usda",
            }
        ],
        "totals": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0},
        "targets": {"calories": 2200, "protein_g": 150, "carbs_g": 220, "fat_g": 70},
        "remaining": {"calories": 2200, "protein_g": 150, "carbs_g": 220, "fat_g": 70},
    }
