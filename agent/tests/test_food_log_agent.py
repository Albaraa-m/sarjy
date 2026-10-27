import json

import pytest
from livekit.agents import AgentSession, RunResult
from livekit.plugins import openai

from memory import UserMemory
from nutrition import DaySummary, FoodLog, FoodMatch, Macros, Nutrition, NutritionTools
from nutrition import db as nutrition_db
from nutrition.food_log import today
from sarjy import Sarjy

BANANA = FoodMatch(id=1, description="Bananas, raw", per_100g=Macros(89, 1.09, 22.84, 0.33))
RICE = FoodMatch(id=2, description="Rice, white, cooked", per_100g=Macros(130, 2.4, 28.6, 0.2))
EGGS = FoodMatch(id=3, description="Egg, scrambled", per_100g=Macros(149, 10, 1.6, 11))
TOAST = FoodMatch(id=4, description="Bread, whole wheat, toasted", per_100g=Macros(306, 13, 51, 4))
MILK = FoodMatch(id=5, description="Milk, whole", per_100g=Macros(61, 3.2, 4.8, 3.3))
# What the LLM may search for -> the one match the stub returns.
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

    async def lookup(self, food: str, grams: float) -> dict:
        found = list(
            {match.id: match for name, match in FOODS.items() if name in food.lower()}.values()
        )
        if not found:
            return {"status": "not_found"}
        self._matches.update({match.id: match for match in found})
        return {
            "status": "found",
            "source": "usda",
            "grams": grams,
            "matches": [
                {"id": m.id, "description": m.description, **vars(m.per_100g.scaled(grams))}
                for m in found
            ],
        }


async def ignore_ui(summary: DaySummary) -> None:
    pass


class Conversation:
    """One session where each `say` is a user turn; collects the tools Sarjy called."""

    def __init__(self, session: AgentSession, food_log: FoodLog):
        self.session = session
        self.food_log = food_log
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
    food_log = await FoodLog.load(user_id, nutrition, on_change=ignore_ui)
    tools = NutritionTools(nutrition, food_log)
    # Same tool-step limit as agent.py, so a meal's lookups and prepares fit in one turn.
    async with AgentSession(llm=llm, max_tool_steps=5) as session:
        await session.start(Sarjy(await UserMemory.load(user_id), tools))
        yield Conversation(session, food_log)


async def test_a_question_is_not_logged(conversation):
    await conversation.say("How many calories are in 118 grams of banana?")
    assert conversation.called("lookup_nutrition")
    assert not conversation.called("prepare_food_log")


async def test_eating_something_prepares_a_log(conversation, user_id):
    reply = await conversation.say("I had a banana this morning.")
    [prepared] = conversation.called("prepare_food_log")
    assert prepared["match_id"] == BANANA.id
    assert "?" in reply, reply
    assert await nutrition_db.foods_on(user_id, today()) == []


async def test_missing_amount_is_asked_first(conversation):
    reply = await conversation.say("I ate some rice.")
    assert not conversation.called("prepare_food_log")
    assert "?" in reply, reply


async def test_yes_saves_it(conversation, user_id):
    await conversation.say("I had a banana this morning.")
    await conversation.say("Yes, log it.")
    assert conversation.called("confirm_food_log")
    [saved] = await nutrition_db.foods_on(user_id, today())
    assert saved.food == BANANA.description


async def test_no_saves_nothing(conversation, user_id):
    await conversation.say("I had a banana this morning.")
    await conversation.say("No, don't log it.")
    assert not conversation.called("confirm_food_log")
    assert await nutrition_db.foods_on(user_id, today()) == []


async def test_correcting_the_amount_prepares_again(conversation):
    await conversation.say("I had a banana this morning.")
    await conversation.say("Actually, it was two bananas.")
    first, second = conversation.called("prepare_food_log")[-2:]
    assert second["grams"] == pytest.approx(2 * first["grams"], rel=0.2)


async def test_food_usda_lacks_is_logged_as_an_estimate(conversation):
    reply = await conversation.say("I had an Al Baik broast meal for lunch.")
    assert conversation.called("prepare_estimated_food_log")
    assert "estimate" in reply or "guess" in reply, reply


async def test_remaining_protein_matches_the_log(conversation):
    await conversation.say("I had a banana this morning.")
    await conversation.say("Yes.")
    reply = await conversation.say("How much protein do I have left today?")
    assert "149" in reply or "148" in reply, reply


async def test_a_meal_prepares_every_food(conversation, user_id):
    reply = await conversation.say(MEAL)
    prepared = {arguments["match_id"] for arguments in conversation.called("prepare_food_log")}
    assert prepared == {EGGS.id, TOAST.id, MILK.id}
    assert not conversation.called("confirm_food_log")
    assert "?" in reply, reply
    assert await nutrition_db.foods_on(user_id, today()) == []


async def test_one_yes_saves_the_whole_meal(conversation, user_id):
    await conversation.say(MEAL)
    await conversation.say("Yes.")
    saved = await nutrition_db.foods_on(user_id, today())
    assert sorted(entry.food for entry in saved) == sorted(
        [EGGS.description, TOAST.description, MILK.description]
    )


async def test_yes_but_without_one_food(conversation, user_id):
    await conversation.say(MEAL)
    await conversation.say("Yes, but no milk.")
    saved = await nutrition_db.foods_on(user_id, today())
    assert sorted(entry.food for entry in saved) == sorted([EGGS.description, TOAST.description])


async def test_correcting_one_food_keeps_the_rest(conversation):
    await conversation.say(MEAL)
    eggs_before = next(
        e for e in conversation.food_log.summary().pending if e.food == EGGS.description
    )
    await conversation.say("Actually, it was two eggs.")
    pending = conversation.food_log.summary().pending
    assert sorted(entry.food for entry in pending) == sorted(
        [EGGS.description, TOAST.description, MILK.description]
    )
    eggs_after = next(e for e in pending if e.food == EGGS.description)
    assert eggs_after.grams < eggs_before.grams
