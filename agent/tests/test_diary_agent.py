import json

import pytest
from livekit.agents import AgentSession, RunResult
from livekit.plugins import openai

from memory import UserMemory
from nutrition import DailyIntake, Diary, Macros, Nutrition, NutritionToolset, UsdaFood
from nutrition import db as nutrition_db
from nutrition.diary import today
from sarjy import Sarjy

BANANA = UsdaFood(
    fdc_id=1,
    description="Bananas, raw",
    per_100g=Macros(calories=89, protein_g=1.09, carbs_g=22.84, fat_g=0.33),
)
RICE = UsdaFood(
    fdc_id=2,
    description="Rice, white, cooked",
    per_100g=Macros(calories=130, protein_g=2.4, carbs_g=28.6, fat_g=0.2),
)
EGGS = UsdaFood(
    fdc_id=3,
    description="Egg, scrambled",
    per_100g=Macros(calories=149, protein_g=10, carbs_g=1.6, fat_g=11),
)
TOAST = UsdaFood(
    fdc_id=4,
    description="Bread, whole wheat, toasted",
    per_100g=Macros(calories=306, protein_g=13, carbs_g=51, fat_g=4),
)
MILK = UsdaFood(
    fdc_id=5,
    description="Milk, whole",
    per_100g=Macros(calories=61, protein_g=3.2, carbs_g=4.8, fat_g=3.3),
)
# What the LLM may search for -> the one USDA food the stub returns.
FOODS = {
    "banana": BANANA,
    "rice": RICE,
    "egg": EGGS,
    "toast": TOAST,
    "bread": TOAST,
    "milk": MILK,
}
MEAL = "Breakfast was three eggs, two slices of toast and a cup of milk."


class StubNutrition(Nutrition):
    """Knows only a few foods, so tests don't depend on USDA's ranking or uptime."""

    async def lookup(self, query: str, grams: float) -> dict:
        found = list(
            {food.fdc_id: food for name, food in FOODS.items() if name in query.lower()}.values()
        )
        if not found:
            return {"status": "not_found"}
        self._usda_foods.update({food.fdc_id: food for food in found})
        return {
            "status": "found",
            "source": "usda",
            "grams": grams,
            "foods": [
                {
                    "fdc_id": f.fdc_id,
                    "description": f.description,
                    **f.per_100g.scaled(grams).model_dump(),
                }
                for f in found
            ],
        }


async def ignore_ui(intake: DailyIntake) -> None:
    pass


class Conversation:
    """One session where each `say` is a user turn; collects the tools Sarjy called."""

    def __init__(self, session: AgentSession, diary: Diary):
        self.session = session
        self.diary = diary
        self.calls: list[tuple[str, dict]] = []

    async def say(self, text: str) -> str:
        result: RunResult = await self.session.run(user_input=text)
        replies = []
        for event in result.events:
            if event.type == "function_call":
                self.calls.append((event.item.name, json.loads(event.item.arguments)))
            elif event.type == "message":
                replies.append(event.item.text_content or "")
        return " ".join(replies).strip().lower()

    def called(self, name: str) -> list[dict]:
        return [arguments for tool, arguments in self.calls if tool == name]


@pytest.fixture
async def conversation(llm: openai.LLM, user_id: str):
    nutrition = StubNutrition()
    diary = await Diary.load(user_id, nutrition, on_change=ignore_ui)
    tools = NutritionToolset(nutrition, diary)
    # Same tool-step limit as agent.py, so a meal's lookups and proposals fit in one turn.
    async with AgentSession(llm=llm, max_tool_steps=5) as session:
        await session.start(Sarjy(await UserMemory.load(user_id), tools))
        yield Conversation(session, diary)


async def test_a_question_is_not_logged(conversation):
    await conversation.say("How many calories are in 118 grams of banana?")
    assert conversation.called("lookup_nutrition")
    assert not conversation.called("propose_portion")


async def test_eating_something_proposes_a_portion(conversation, user_id):
    reply = await conversation.say("I had a banana this morning.")
    [proposed] = conversation.called("propose_portion")
    assert proposed["fdc_id"] == BANANA.fdc_id
    assert "?" in reply, reply
    assert await nutrition_db.eaten_on(user_id, today()) == []


async def test_missing_amount_is_asked_first(conversation):
    reply = await conversation.say("I ate some rice.")
    assert not conversation.called("propose_portion")
    assert "?" in reply, reply


async def test_yes_saves_it(conversation, user_id):
    await conversation.say("I had a banana this morning.")
    await conversation.say("Yes, log it.")
    assert conversation.called("confirm_portions")
    [saved] = await nutrition_db.eaten_on(user_id, today())
    assert saved.usda_description == BANANA.description


async def test_no_saves_nothing(conversation, user_id):
    await conversation.say("I had a banana this morning.")
    await conversation.say("No, don't log it.")
    assert not conversation.called("confirm_portions")
    assert await nutrition_db.eaten_on(user_id, today()) == []


async def test_correcting_the_amount_proposes_again(conversation):
    await conversation.say("I had a banana this morning.")
    await conversation.say("Actually, it was two bananas.")
    first, second = conversation.called("propose_portion")[-2:]
    assert second["grams"] == pytest.approx(2 * first["grams"], rel=0.2)


async def test_food_usda_lacks_is_logged_as_an_estimate(conversation):
    reply = await conversation.say("I had an Al Baik broast meal for lunch.")
    assert conversation.called("propose_estimated_portion")
    assert "estimate" in reply or "guess" in reply, reply


async def test_remaining_protein_matches_the_log(conversation):
    await conversation.say("I had a banana this morning.")
    await conversation.say("Yes.")
    reply = await conversation.say("How much protein do I have left today?")
    assert "149" in reply or "148" in reply, reply


async def test_a_meal_proposes_every_food(conversation, user_id):
    reply = await conversation.say(MEAL)
    proposed = {arguments["fdc_id"] for arguments in conversation.called("propose_portion")}
    assert proposed == {EGGS.fdc_id, TOAST.fdc_id, MILK.fdc_id}
    assert not conversation.called("confirm_portions")
    assert "?" in reply, reply
    assert await nutrition_db.eaten_on(user_id, today()) == []


async def test_one_yes_saves_the_whole_meal(conversation, user_id):
    await conversation.say(MEAL)
    await conversation.say("Yes.")
    saved = await nutrition_db.eaten_on(user_id, today())
    assert sorted(portion.usda_description or "" for portion in saved) == sorted(
        [EGGS.description, TOAST.description, MILK.description]
    )


async def test_yes_but_without_one_food(conversation, user_id):
    await conversation.say(MEAL)
    await conversation.say("Yes, but no milk.")
    saved = await nutrition_db.eaten_on(user_id, today())
    assert sorted(portion.usda_description or "" for portion in saved) == sorted(
        [EGGS.description, TOAST.description]
    )


async def test_correcting_one_food_keeps_the_rest(conversation):
    await conversation.say(MEAL)
    eggs_before = next(
        e for e in conversation.diary.intake().pending if e.usda_description == EGGS.description
    )
    await conversation.say("Actually, it was two eggs.")
    pending = conversation.diary.intake().pending
    assert sorted(portion.usda_description or "" for portion in pending) == sorted(
        [EGGS.description, TOAST.description, MILK.description]
    )
    eggs_after = next(e for e in pending if e.usda_description == EGGS.description)
    assert eggs_after.grams < eggs_before.grams
