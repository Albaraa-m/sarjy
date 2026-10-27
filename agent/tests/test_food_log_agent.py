import json

import pytest
from livekit.agents import AgentSession, RunResult
from livekit.plugins import openai

from memory import UserMemory
from nutrition import DaySummary, FoodLog, FoodMatch, Macros, Nutrition, NutritionTools
from nutrition import db as nutrition_db
from nutrition.food_log import today
from sarjy import Sarjy

FOODS = {
    "banana": FoodMatch(id=1, description="Bananas, raw", per_100g=Macros(89, 1.09, 22.84, 0.33)),
    "rice": FoodMatch(
        id=2, description="Rice, white, cooked", per_100g=Macros(130, 2.4, 28.6, 0.2)
    ),
}


class StubNutrition(Nutrition):
    """Knows only banana and rice, so tests don't depend on USDA's ranking or uptime."""

    async def lookup(self, food: str, grams: float) -> dict:
        found = [match for name, match in FOODS.items() if name in food.lower()]
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

    def __init__(self, session: AgentSession):
        self.session = session
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
    async with AgentSession(llm=llm) as session:
        await session.start(Sarjy(await UserMemory.load(user_id), tools))
        yield Conversation(session)


async def test_a_question_is_not_logged(conversation):
    await conversation.say("How many calories are in 118 grams of banana?")
    assert conversation.called("lookup_nutrition")
    assert not conversation.called("prepare_food_log")


async def test_eating_something_prepares_a_log(conversation, user_id):
    reply = await conversation.say("I had a banana this morning.")
    [prepared] = conversation.called("prepare_food_log")
    assert prepared["match_id"] == FOODS["banana"].id
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
    assert saved.food == FOODS["banana"].description


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
